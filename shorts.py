###TODO
'''
integrate subtitles
auto title and caption, probably based on generated subtitles
auto post
POSSIBLY make a django webapp


'''
from moviepy.editor import VideoFileClip, concatenate_videoclips
from scenedetect import VideoManager, SceneManager
from scenedetect.detectors import ContentDetector
from deepface import DeepFace
import os
import cv2
import numpy as np
import shutil
from subtitles import generate_subtitles

video_folder = "/home/loganh/Torrent/House MD"
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

def ensure_temp_directory(temp_folder="temp_scenes"):
    #Ensure that the temp folder exists
    if not os.path.exists(temp_folder):
        os.makedirs(temp_folder)
    return temp_folder




def detect_scenes(video_path, threshold=30):
    """Detects initial scenes using the specified threshold."""
    # Create a video manager object
    videoManager = VideoManager([video_path])
    sceneManager = SceneManager()
    sceneManager.add_detector(ContentDetector(threshold=threshold))

    # Start the video manager
    videoManager.start()

    # Detect scenes
    sceneManager.detect_scenes(videoManager)

    # Get detected scenes
    scene_list = sceneManager.get_scene_list()

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
            try:
                os.remove(temp_scene_path)
            except:
                pass
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

def crop_and_resize_clip(clip, target_width=405, target_height=720):
    """
    Crop and resize a clip to match the target resolution (405x720).
    
    Parameters:
        clip (VideoFileClip): The input video clip to be processed.
        target_width (int): The target width of the final clip.
        target_height (int): The target height of the final clip.
    
    Returns:
        VideoFileClip: The cropped and resized video clip.
    """
    # Get the current dimensions of the clip
    clip_width, clip_height = clip.size

    # Calculate the aspect ratios
    target_aspect_ratio = target_width / target_height
    clip_aspect_ratio = clip_width / clip_height

    # Determine cropping dimensions to center the frame
    if clip_aspect_ratio > target_aspect_ratio:
        # Crop width to match the target aspect ratio
        new_width = int(clip_height * target_aspect_ratio)
        x1 = (clip_width - new_width) // 2
        x2 = x1 + new_width
        y1, y2 = 0, clip_height
    else:
        # Crop height to match the target aspect ratio
        new_height = int(clip_width / target_aspect_ratio)
        y1 = (clip_height - new_height) // 2
        y2 = y1 + new_height
        x1, x2 = 0, clip_width

    # Crop the clip to the calculated dimensions
    cropped_clip = clip.crop(x1=x1, y1=y1, x2=x2, y2=y2)

    # Resize the cropped clip to the target dimensions
    resized_clip = cropped_clip.resize(width=target_width, height=target_height)

    return resized_clip



def save_top_scenes(top_scenes, episode_output_dir, target_width=405, target_height=720):
    """Save the top N scenes to the episode's output folder."""
    # Ensure the directory exists (already created by create_episode_output_directory)
    if os.path.exists(episode_output_dir):
        shutil.rmtree(episode_output_dir)
    if not os.path.exists(episode_output_dir):
        os.makedirs(episode_output_dir)
    
    for idx, (scene_clip, score) in enumerate(top_scenes):
        try:
            # Crop and resize the clip to 405x720
            processed_clip = crop_and_resize_clip(scene_clip, target_width, target_height)

            # Save the processed clip
            output_path = os.path.join(episode_output_dir, f"scene_{idx+1}_score_{score}.mp4")
            print(f"Saving cropped and resized scene {idx+1} to {output_path}...")
            processed_clip.write_videofile(output_path, codec="libx264")
            print(f"Scene {idx+1} saved to {output_path}.")
        except Exception as e:
            print(f"Error saving scene {idx+1}: {e}")






def detect_face(frame):
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, 1.1, 4)
    return faces



def create_episode_output_directory(video_path):
    """Create an output directory for each episode based on the video filename."""
    # Extract episode name from the video filename
    episode_name = os.path.splitext(os.path.basename(video_path))[0]
    episode_output_dir = os.path.join(os.path.dirname(video_path), f"{episode_name} output")

    # Ensure the directory exists
    if not os.path.exists(episode_output_dir):
        os.makedirs(episode_output_dir)
    
    print ("This is the output directory: ", episode_output_dir )

    return episode_output_dir




for filename in os.listdir(video_folder):
    if filename.endswith(".mkv") or filename.endswith(".m4v"):  
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
        cpy = os.listdir(episode_output_dir).copy()
        print(cpy)
        for top_scene in cpy:
            generate_subtitles(episode_output_dir + "/" + top_scene, video_path)





print("Processing complete.")   