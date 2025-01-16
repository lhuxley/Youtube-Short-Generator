


import whisper
from moviepy.editor import VideoFileClip, TextClip, CompositeVideoClip
from pysrt import SubRipFile, SubRipItem, SubRipTime
from moviepy.video.tools.subtitles import SubtitlesClip
import os
import sys
from collections import Counter
import re
from transformers import pipeline


def extract_dialogue_phrases(subtitle_path):
    with open(subtitle_path, 'r') as file:
        subtitles = file.read()

    # Extract all dialogue phrases
    phrases = re.findall(r'(?<=\n)(.*?)(?=\n\n)', subtitles)
    return [phrase.strip() for phrase in phrases if len(phrase.split()) > 3]

def get_most_dramatic_phrase(phrases):
    # Load sentiment analysis model
    sentiment_analyzer = pipeline("sentiment-analysis")
    
    # Analyze sentiment for each phrase
    sentiment_scores = [(phrase, sentiment_analyzer(phrase)[0]['score']) for phrase in phrases]

    most_dramatic = max(sentiment_scores, key=lambda x: x[1])
    return most_dramatic[0]

def generate_title(subtitle_path):
    phrases = extract_dialogue_phrases(subtitle_path)
    if not phrases:
        return "Unexpected Moments"
    
    dramatic_phrase = get_most_dramatic_phrase(phrases)
    return f'"{dramatic_phrase}"'




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
    save_scenes_with_appended_subtitles(video, video_path)





def format_subtitles(txt):
    return TextClip(txt, font='Arial', fontsize=40, color='white', size=(405, None), align='center', method='caption')


def save_scenes_with_appended_subtitles(video, video_path):
    subtitles = SubtitlesClip("temp.srt", format_subtitles)


    final_video = CompositeVideoClip([video, subtitles.set_position(('center', video.h - 150))])

    title = generate_title("temp.srt")

    final_video.write_videofile(sys.argv[1] + "/"+ title + "| House MD.mp4", fps=video.fps)

    os.remove("temp.srt")
    os.remove(video_path)
    os.remove("audio.wav")
    

cpy = os.listdir( sys.argv[1]).copy()
for top_scene in cpy:
    generate_subtitles(sys.argv[1] + "/" + top_scene)