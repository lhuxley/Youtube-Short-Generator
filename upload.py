import os
import pickle 
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow

CREDENTIALS_FILE = "token.pickle"
CLIENT_SECRET_FILE = "client_secret_92211281326-hra7dthtde2t8ms3gjebqp7tpuoake9s.apps.googleusercontent.com.json"

def authenticate_youtube():
    scopes = ["https://www.googleapis.com/auth/youtube.upload"]

    credentials = None
    if os.path.exists(CREDENTIALS_FILE):
        with open(CREDENTIALS_FILE, "rb") as token:
            credentials = pickle.load(token)
            
    if not credentials or not credentials.valid:
        flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_FILE, scopes)
        credentials = flow.run_local_server(port=0)
        # Save the credentials for future use
        with open(CREDENTIALS_FILE, "wb") as token:
            pickle.dump(credentials, token)
    
    return build("youtube", "v3", credentials=credentials)

def upload_video(video_path, title, description, tags, privacyStatus, youtube):
    request_body = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": tags,
            "categoryId": "24", 
        },
        "status": {
            "privacyStatus": privacyStatus,  
        },
    }
    
    media_file = MediaFileUpload(video_path, chunksize=-1, resumable=True)
    response = youtube.videos().insert(
        part="snippet,status", body=request_body, media_body=media_file
    ).execute()

    print("Video uploaded. Video ID:", response["id"])


'''
if __name__ == "__main__":
    
    video_path = "/home/loganh/Torrent/House MD/House - S06E14 - Private Lives output/\"And you're a big part of that.\"| House MD.mp4"
    title = '"The Most Dramatic Moment!"'
    description = "Check out this exciting scene! More content coming soon."
    tags = ["drama", "scenes", "shorts", "entertainment"]

    upload_video(video_path, title, description, tags, True)
'''