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




def detect_scenes(video_path):
    # Create a video manager object
    video_manager = VideoManager([video_path])
    
    # Create a scene manager and add a content detector (default threshold = 30)
    scene_manager = SceneManager()
    scene_manager.add_detector(ContentDetector(threshold=55))

    # Start the video manager
    video_manager.start()

    # Detect scenes
    scene_manager.detect_scenes(video_manager)

    # Get scene list
    scene_list = scene_manager.get_scene_list()

    # Print out scene start and end times
    print(f"Detected {len(scene_list)} scenes.")
    for i, scene in enumerate(scene_list):
        print(f"Scene {i+1}: Start {scene[0].get_timecode()}, End {scene[1].get_timecode()}")
    
    # Return scene list for further processing
    return scene_list


def cut_scenes(video_path, scene_list):
    """Cut scenes from the video based on the detected scene list."""
    clip = VideoFileClip(video_path)
    scene_scores = []

    # Process each scene and score it based on emotion
    for idx, scene in enumerate(scene_list):
        start_time = scene[0].get_seconds()
        end_time = scene[1].get_seconds()
        scene_clip = clip.subclip(start_time, end_time)

        # Analyze emotion for the scene
        scene_score = analyze_emotion_for_scene(scene_clip)

        scene_scores.append((scene_clip, scene_score))

        print(f"Scene {idx+1} score: {scene_score}")

    return scene_scores


def analyze_emotion_for_scene(scene_clip):
    emotions = []

    # Analyze one frame per second (you can adjust fps)
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
            print(f"Detected emotion: {emotion}")

        except Exception as e:
            # If no face is detected or there's an error, print a warning and skip the frame
            print(f"Warning: No face detected in frame. Skipping... {str(e)}")

    # Score the scene based on detected emotions
    emotional_intensity = {
        'happy': 1, 'sad': 3, 'neutral': 1, 'angry': 3, 'fear': 3, 'surprise': 2, 'disgust': 2, 'contempt': 2, 'Dr. House': 8, 'Hugh Laurie': 10
    }
    emotion_score = sum(emotional_intensity.get(e, 0) for e in emotions)
    return emotion_score




def save_top_scenes(top_scenes, episode_output_dir):
    """Save the top N scenes to the episode's output folder."""
    # Ensure the directory exists (already created by create_episode_output_directory)
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




# Process each video file in the folder
for filename in os.listdir(video_folder):
    if filename.endswith(".mkv") :  # Add any other video formats you want to process
        video_path = os.path.join(video_folder, filename)
        print(f"Processing video: {video_path}")

        ensure_temp_directory()
        episode_output_dir = create_episode_output_directory(video_path)
        # Detect scenes
        scene_list = detect_scenes(video_path)

        # Cut scenes into clips
        #scene_clips = cut_scenes(video_path, scene_list)

        # Apply dynamic cropping to each scene
        #cropped_clips = [clip.fl(dynamic_crop) for clip in scene_list]

        # Concatenate all cropped clips into one video
        #cropped_clip = concatenate_videoclips(cropped_clips)

        # Save the final cropped video
        #output_video_path = os.path.join(video_folder, f"{os.path.splitext(filename)[0]}_cropped.mp4")
        #cropped_clip.write_videofile(output_video_path, codec="libx264")

        scene_scores = cut_scenes(video_path, scene_list)

        # Sort the scenes based on their emotional score in descending order
        top_scenes = sorted(scene_scores, key=lambda x: x[1], reverse=True)[:5]

        # Save the top 5 scenes
        save_top_scenes(top_scenes, episode_output_dir)

print("Processing complete.")   