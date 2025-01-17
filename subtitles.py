

import os
import sys
import json
import re
import whisper
from moviepy.editor import VideoFileClip, TextClip, CompositeVideoClip
from moviepy.video.tools.subtitles import SubtitlesClip
from transformers import pipeline
from upload import upload_video

def extract_dialogue_phrases(subtitle_path):
    with open(subtitle_path, 'r', encoding='utf-8') as file:
        subtitles = file.read()

    phrases = re.findall(r'(?<=\n)(.*?)(?=\n\n)', subtitles)
    return [phrase.strip() for phrase in phrases if len(phrase.split()) > 3]

def get_most_dramatic_phrase(phrases):
    sentiment_analyzer = pipeline("sentiment-analysis")
    
    sentiment_scores = [(phrase, sentiment_analyzer(phrase)[0]['score']) for phrase in phrases]

    most_dramatic = max(sentiment_scores, key=lambda x: x[1])
    return most_dramatic[0]

def generate_title(subtitle_path):
    phrases = extract_dialogue_phrases(subtitle_path)
    if not phrases:
        return "Unexpected Moments"
    
    dramatic_phrase = get_most_dramatic_phrase(phrases)
    return "\"" + dramatic_phrase + "\"" + " | #Shorts | House M.D."




def format_time_with_milliseconds(seconds):
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds - int(seconds)) * 1000)
    return f"{hours:02}:{minutes:02}:{secs:02},{millis:03}"

def extract_audio(video_path, audio_path="audio.wav"):
    clip = VideoFileClip(video_path)
    clip.audio.write_audiofile(audio_path)
    return audio_path





def generate_subtitles(video_path, model_name="base", output_srt="temp.srt"):


    video = VideoFileClip(video_path)
    audio_path = extract_audio(video_path)
    model = whisper.load_model(model_name)
    result = model.transcribe(audio_path, word_timestamps=True)

    model_path = os.path.abspath("models/base.pt")
            
    print(f"Loading model from: {model_path}")

    with open(output_srt, "w") as file:
        for i, segment in enumerate(result["segments"]):
            print(segment["start"])
            print(segment["end"])
            start_time = format_time_with_milliseconds(segment["start"])
            end_time = format_time_with_milliseconds(segment["end"])
            if start_time == end_time:
                continue 
            text = segment["text"]
            file.write(f"{i + 1}\n{start_time} --> {end_time}\n{text}\n\n")
    
    print(f"Subtitles saved to {output_srt}")
    final_path = save_scenes_with_appended_subtitles(video, video_path)
    return final_path






def format_subtitles(txt):
    return TextClip(txt, font='Arial', fontsize=40, color='white', size=(405, None), align='center', method='caption')


def save_scenes_with_appended_subtitles(video, video_path):
    subtitles = SubtitlesClip("temp.srt", format_subtitles)


    final_video = CompositeVideoClip([video, subtitles.set_position(('center', video.h - 150))])

    
    final_path = sys.argv[1] + "subtitled.mp4"

    final_video.write_videofile(final_path, fps=video.fps)

    
    os.remove(video_path)
    os.remove("audio.wav")

    return final_path
    
if __name__ == "__main__":
    with open('config.json', 'r', encoding='utf-8') as file:
        data = json.load(file)
    cpy = os.listdir( sys.argv[1]).copy()
    for top_scene in cpy:
        new_video_path = generate_subtitles(sys.argv[1] + "/" + top_scene)
        if data["autoUpload"] == "True":
            title = generate_title("temp.srt")
            upload_video(new_video_path, title,"Check out this exciting scene! More content coming soon.",  ["drama", "scenes", "shorts", "entertainment"], data["privacyStatus"])
            os.remove("temp.srt")
