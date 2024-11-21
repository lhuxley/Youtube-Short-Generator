from moviepy.editor import VideoFileClip, concatenate_videoclips
from scenedetect import VideoManager, SceneManager
from scenedetect.detectors import ContentDetector
from deepface import DeepFace
import os
import cv2
import numpy as np
import shutil

video_folder = "/home/loganh/Torrent/House MD Season 3"
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

def ensure_temp_directory(temp_folder="temp_scenes"):
    #Ensure that the temp folder exists
    if not os.path.exists(temp_folder):
        os.makedirs(temp_folder)
    return temp_folder




def detect_scenes(video_path, threshold=30):
    """Detects initial scenes using the specified threshold."""
    # Create a video manager object
    video_manager = VideoManager([video_path])
    scene_manager = SceneManager()
    scene_manager.add_detector(ContentDetector(threshold=threshold))

    # Start the video manager
    video_manager.start()

    # Detect scenes
    scene_manager.detect_scenes(video_manager)

    # Get detected scenes
    scene_list = scene_manager.get_scene_list()

    print(f"Initial detection found {len(scene_list)} scenes.")
    return scene_list


def refine_scenes(video_path, scene_list, max_scene_length=60, threshold_step=5, min_threshold=15):
    """Refines scene list, splitting any scene over max_scene_length recursively."""
    refined_scenes = []
    for scene in scene_list:
        start_time = scene[0].get_seconds()
        end_time = scene[1].get_seconds()
        duration = end_time - start_time

        if duration > max_scene_length:
            # Refine scene by re-detecting with a stricter threshold
            print(f"Refining scene: Start {scene[0].get_timecode()}, End {scene[1].get_timecode()}, Duration: {duration:.2f} seconds.")
            
            # Extract the portion of the video corresponding to this scene
            temp_scene_path = "temp_scene.mp4"
            VideoFileClip(video_path).subclip(start_time, end_time).write_videofile(temp_scene_path, codec="libx264")

            # Run detection on the smaller scene with an adjusted threshold
            new_threshold = max(min_threshold, threshold_step)
            new_scene_list = detect_scenes(temp_scene_path, threshold=new_threshold)

            # Recur to ensure all sub-scenes are under the max length
            refined_scenes.extend(refine_scenes(temp_scene_path, new_scene_list, max_scene_length))
            
            # Clean up temporary files
            os.remove(temp_scene_path)
        else:
            refined_scenes.append(scene)
    
    return refined_scenes
    
    # Return scene list for further processing
    return scene_list


def process_scenes(video_path, scene_list):
    """Cut scenes from the video based on the detected scene list."""
    clip = VideoFileClip(video_path)
    scene_scores = []

    # Process each scene and score it based on emotion
    for idx, scene in enumerate(scene_list):
        start_time = scene[0].get_seconds()
        end_time = scene[1].get_seconds()
        scene_clip = clip.subclip(start_time, end_time)
        length = end_time - start_time
        # Analyze emotion for the scene
        if length >= 20:
            scene_score = score_scene(scene_clip)

            scene_scores.append((scene_clip, scene_score))

            print(f"Scene {idx+1} score: {scene_score} length: { (length)}")

    return scene_scores


dr_house_image = cv2.imread("drhouse.jpg")
dr_house_face = DeepFace.extract_faces(dr_house_image, detector_backend='opencv')  # Detect the face in the reference image

def score_scene(scene_clip):
    emotions = []
    dr_house_score = 0  
    for frame in scene_clip.iter_frames(fps=1):
        try:
            # Analyze emotions in the frame
            result = DeepFace.analyze(frame, actions=['emotion'])

            # Check if the result is a list (which seems to be the case)
            if isinstance(result, list):
                result = result[0]  # Access the first dictionary from the list
            
            # Extract the dominant emotion
            emotion = result['dominant_emotion']
            emotions.append(emotion)
            
            # Detect faces in the frame
            detected_faces = DeepFace.extract_faces(frame, detector_backend='opencv')
            try:
                #  Check if Dr. House's face is detected in the frame
                match = DeepFace.verify(frame, "drhouse.jpg" )
                
                if match['verified']:
                    print("Dr. House detected in this scene!")
                    dr_house_score += 5  # Increase score for Dr. House presence


            except Exception as z:
                print(f"House face detection messed up :{frame, str(z)}")
        except Exception as e:
            pass
            

    # Calculate the scene's total emotional score
    emotional_intensity = {
        'happy': 1, 'sad': 3, 'neutral': 1, 'angry': 3, 'fear': 3, 'surprise': 2, 'disgust': 2, 'contempt': 2, 
    }
    emotion_score = sum(emotional_intensity.get(e, 0) for e in emotions)

    # Add the Dr. House score to the total
    total_score = emotion_score + dr_house_score
    return total_score




def save_top_scenes(top_scenes, episode_output_dir):
    """Save the top N scenes to the episode's output folder."""
    # Ensure the directory exists (already created by create_episode_output_directory)
    if os.path.exists(episode_output_dir):
        shutil.rmtree(episode_output_dir)
    if not os.path.exists(episode_output_dir):
        os.makedirs(episode_output_dir)
    
    for idx, (scene_clip, score) in enumerate(top_scenes):
        try:
            # Save each clip with a filename indicating its score
            output_path = os.path.join(episode_output_dir, f"scene_{idx+1}_score_{score}.mp4")
            print(f"Saving scene {idx+1} to {output_path}...")
            scene_clip.write_videofile(output_path, codec="libx264")
            print(f"Scene {idx+1} saved to {output_path}.")
        except Exception as e:
            print(f"Error saving scene {idx+1}: {e}")




def detect_face(frame):
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, 1.1, 4)
    return faces

# Function to dynamically crop video based on face location
def dynamic_crop(get_frame, t):
    frame = get_frame(t)
    faces = detect_face(frame)

    if len(faces) > 0:
        # Take the first detected face for simplicity
        x, y, w, h = faces[0]
        center_x, center_y = x + w // 2, y + h // 2
    else:
        # No face detected, center the frame manually
        print("Warning: No face detected in frame. Centering frame...")
        center_x, center_y = frame.shape[1] // 2, frame.shape[0] // 2

    # Define cropping area (keeping face in center or centering frame)
    crop_width = 1920
    crop_height = 1080
    start_x = max(0, center_x - crop_width // 2)
    start_y = max(0, center_y - crop_height // 2)
    
    # Ensure we don't go out of frame bounds
    start_x = min(start_x, frame.shape[1] - crop_width)
    start_y = min(start_y, frame.shape[0] - crop_height)

    cropped_frame = frame[start_y:start_y + crop_height, start_x:start_x + crop_width]
    return cropped_frame


def create_episode_output_directory(video_path):
    """Create an output directory for each episode based on the video filename."""
    # Extract episode name from the video filename
    episode_name = os.path.splitext(os.path.basename(video_path))[0]
    episode_output_dir = os.path.join(os.path.dirname(video_path), f"{episode_name} output")

    # Ensure the directory exists
    if not os.path.exists(episode_output_dir):
        os.makedirs(episode_output_dir)
    
    return episode_output_dir




for filename in os.listdir(video_folder):
    if filename.endswith(".mkv"):  # Add any other video formats you want to process
        video_path = os.path.join(video_folder, filename)
        print(f"Processing video: {video_path}")

        # Ensure necessary directories exist
        ensure_temp_directory()
        episode_output_dir = create_episode_output_directory(video_path)

        # Detect initial scenes
        initial_scenes = detect_scenes(video_path, threshold=55)  # First pass

        # Refine scenes to ensure all are under the max length
        final_scenes = refine_scenes(video_path, initial_scenes, max_scene_length=60)

        # Cut scenes into clips and score them
        scene_scores = process_scenes(video_path, final_scenes)

        # Sort the scenes based on their emotional score in descending order
        top_scenes = sorted(scene_scores, key=lambda x: x[1], reverse=True)[:5]

        # Save the top 5 scenes
        save_top_scenes(top_scenes, episode_output_dir)



print("Processing complete.")   