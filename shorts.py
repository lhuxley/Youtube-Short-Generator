###TODO
'''

auto title and caption, probably based on generated subtitles
auto post
support different resolutions



'''
from moviepy.editor import VideoFileClip, concatenate_videoclips
from scenedetect import VideoManager, SceneManager
from scenedetect.detectors import ContentDetector
from deepface import DeepFace
import os
import cv2
import numpy as np
import shutil
import subprocess
import json







def ensure_temp_directory(temp_folder="temp_scenes"):
    #Ensure that the temp folder exists
    if not os.path.exists(temp_folder):
        os.makedirs(temp_folder)
    return temp_folder




def detect_scenes(video_path, threshold=30):

    videoManager = VideoManager([video_path])
    sceneManager = SceneManager()
    sceneManager.add_detector(ContentDetector(threshold=threshold))

    videoManager.start()

    sceneManager.detect_scenes(videoManager)

    scene_list = sceneManager.get_scene_list()

    print(f"Initial detection found {len(scene_list)} scenes.")
    return scene_list


def refine_scenes(video_path, scene_list, max_scene_length=60, threshold_step=5, min_threshold=15):
    refined_scenes = []
    for scene in scene_list:
        start_time = scene[0].get_seconds()
        end_time = scene[1].get_seconds()
        duration = end_time - start_time

        if duration > max_scene_length:

            print(f"Refining scene: Start {scene[0].get_timecode()}, End {scene[1].get_timecode()}, Duration: {duration:.2f} seconds.")
            
            # Extract the portion of the video corresponding to this scene
            temp_scene_path = "temp_scene.mp4"
            VideoFileClip(video_path).subclip(start_time, end_time).write_videofile(temp_scene_path, codec="libx264")

            # Run detection on the smaller scene with an adjusted threshold
            new_threshold = max(min_threshold, threshold_step)
            new_scene_list = detect_scenes(temp_scene_path, threshold=new_threshold)

            # Recur to ensure all sub-scenes are under the max length
            refined_scenes.extend(refine_scenes(temp_scene_path, new_scene_list, max_scene_length))

            os.remove(temp_scene_path)

        else:
            refined_scenes.append(scene)
    
    return refined_scenes
    


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




def score_scene(scene_clip):
    emotions = []
    detecterPersonScore = 0  
    for frame in scene_clip.iter_frames(fps=1):
        try:
            
            result = DeepFace.analyze(frame, actions=['emotion'])


            if isinstance(result, list):
                result = result[0]  

            emotion = result['dominant_emotion']
            emotions.append(emotion)
            
            detected_faces = DeepFace.extract_faces(frame, detector_backend='opencv')
            try:
                match = DeepFace.verify(frame, data["facePath"] )
                
                if match['verified']:
                    print("Provided face detected in this scene!")
                    detecterPersonScore += 5  


            except Exception as z:
                print(f"Face detection messed up :{frame, str(z)}")
        except Exception as e:
            pass
            
    emotional_intensity = data["emotionsScore"]
    emotion_score = sum(emotional_intensity.get(e, 0) for e in emotions)

    total_score = emotion_score + detecterPersonScore
    return total_score

def crop_and_resize_clip(clip, target_width=405, target_height=720):

    clip_width, clip_height = clip.size

    target_aspect_ratio = target_width / target_height
    clip_aspect_ratio = clip_width / clip_height

    if clip_aspect_ratio > target_aspect_ratio:
        new_width = int(clip_height * target_aspect_ratio)
        x1 = (clip_width - new_width) // 2
        x2 = x1 + new_width
        y1, y2 = 0, clip_height
    else:
        new_height = int(clip_width / target_aspect_ratio)
        y1 = (clip_height - new_height) // 2
        y2 = y1 + new_height
        x1, x2 = 0, clip_width

    cropped_clip = clip.crop(x1=x1, y1=y1, x2=x2, y2=y2)

    resized_clip = cropped_clip.resize(width=target_width, height=target_height)

    return resized_clip



def save_top_scenes(top_scenes, episode_output_dir, target_width=405, target_height=720):

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





with open('config.json', 'r', encoding='utf-8') as file:
    data = json.load(file)

    
video_folder = data["videoFolder"]
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
face_image = cv2.imread(data["facePath"])
deep_face = DeepFace.extract_faces(face_image, detector_backend='opencv')  

for filename in os.listdir(video_folder):
    if filename.endswith(".mkv") or filename.endswith(".m4v"):  
        videoPath = os.path.join(video_folder, filename)
        print(f"Processing video: {videoPath}")

        ensure_temp_directory()
        episode_output_dir = create_episode_output_directory(videoPath)


        initial_scenes = detect_scenes(videoPath, threshold=55) 

        final_scenes = refine_scenes(videoPath, initial_scenes, max_scene_length=60)

        scene_scores = process_scenes(videoPath, final_scenes)

        top_scenes = sorted(scene_scores, key=lambda x: x[1], reverse=True)[:int(data["topXClips"])]

        save_top_scenes(top_scenes, episode_output_dir)

        subprocess.run(['python', 'subtitles.py', episode_output_dir], check = False)






print("Processing complete.")   