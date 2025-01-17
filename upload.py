import os
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow
import sys

def authenticate_youtube():
    # Authenticate using OAuth
    scopes = ["https://www.googleapis.com/auth/youtube.upload"]
    flow = InstalledAppFlow.from_client_secrets_file("client_secret_92211281326-hra7dthtde2t8ms3gjebqp7tpuoake9s.apps.googleusercontent.com.json", scopes)
    credentials = flow.run_local_server(port=0)  # Use local server for authentication
    return build("youtube", "v3", credentials=credentials)


def upload_video(youtube, video_path, title, description, tags):
    request_body = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": tags,
            "categoryId": "24", 
        },
        "status": {
            "privacyStatus": "public",  
        },
    }
    
    media_file = MediaFileUpload(video_path, chunksize=-1, resumable=True)
    response = youtube.videos().insert(
        part="snippet,status", body=request_body, media_body=media_file
    ).execute()

    print("Video uploaded. Video ID:", response["id"])



youtube = authenticate_youtube()
video_path = "/home/loganh/Torrent/House MD/House - S06E14 - Private Lives output/\"And you're a big part of that.\"| House MD.mp4"
title = '"The Most Dramatic Moment!"'
description = "Check out this exciting scene! More content coming soon."
tags = ["drama", "scenes", "shorts", "entertainment"]

upload_video(youtube, video_path, title, description, tags)
