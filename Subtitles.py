videoPath = "/home/loganh/Torrent/House MD/House - S03E03 - Informed Consent output/scene_1_score_152.mp4"


import whisper
from moviepy.editor import VideoFileClip, TextClip, CompositeVideoClip
from pysrt import SubRipFile, SubRipItem, SubRipTime
from moviepy.video.tools.subtitles import SubtitlesClip


def format_time_with_milliseconds(seconds):
    """Convert seconds to SRT-compatible timestamp with millisecond precision."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds - int(seconds)) * 1000)
    return f"{hours:02}:{minutes:02}:{secs:02},{millis:03}"

def extract_audio(video_path, audio_path="audio.wav"):
    clip = VideoFileClip(video_path)
    clip.audio.write_audiofile(audio_path)
    return audio_path

def generate_subtitles(video_path, model_name="small", output_srt="subtitles.srt"):
    audio_path = extract_audio(video_path)
    model = whisper.load_model(model_name)
    result = model.transcribe(audio_path, word_timestamps=True)

    with open(output_srt, "w") as file:
        for i, segment in enumerate(result["segments"]):
            print(segment["start"])
            print(segment["end"])
            start_time = format_time_with_milliseconds(segment["start"])
            end_time = format_time_with_milliseconds(segment["end"])
            text = segment["text"]
            file.write(f"{i + 1}\n{start_time} --> {end_time}\n{text}\n\n")
    
    print(f"Subtitles saved to {output_srt}")


def subtitle_generator(txt):
    return TextClip(txt, font='Arial', fontsize=24, color='white', size=(405, None), align='center', method='caption')

video = VideoFileClip(videoPath)
# Usage
generate_subtitles(videoPath)

subtitles = SubtitlesClip("subtitles.srt", subtitle_generator)


final_video = CompositeVideoClip([video, subtitles.set_position(('center', video.h - 150))])
final_video.write_videofile("output_with_subtitles.mp4", fps=video.fps)