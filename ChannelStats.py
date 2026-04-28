import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import re
from pyairtable import Api
import requests
from googleapiclient.discovery import build
from urllib.parse import urlparse, parse_qs
import sys
from datetime import datetime
import isodate
import math

now = datetime.now()
import json

with open("config.json") as f:
    config = json.load(f)

api_key = config["airtable"]["api_key"]
base_id = config["airtable"]["base_id"]
table_name = config["airtable"]["table_name"]
api = Api(api_key)

# Define the scope
scope = [
    'https://www.googleapis.com/auth/spreadsheets',
    "https://www.googleapis.com/auth/drive"
]


# Add credentials
creds = Credentials.from_service_account_file(credsPath, scopes=scope)
# Authenticate and create the client
client = gspread.authorize(creds)
youtube = build("youtube", "v3", developerKey=APIKey)


def is_vertical(embed_html):
    """
    Detect if the video is vertical (aspect ratio ~9:16) from embed HTML.
    """
    match = re.search(r'width="(\d+)"\s+height="(\d+)"', embed_html)
    if match:
        width, height = int(match.group(1)), int(match.group(2))
        if height > width:  # Vertical video
            return True
    return False

# Function to get channel's latest videos and stats
def get_latest_videos(channel_id, min_results=5, max_results=50):
    videos = []
    try:
        youtube = build("youtube", "v3", developerKey=APIKey)

        # Step 1: Get the Uploads playlist ID for the channel
        channel_response = youtube.channels().list(
            part="contentDetails",
            id=channel_id
        ).execute()

        if not channel_response["items"]:
            print("Channel not found.")
            return

        uploads_playlist_id = channel_response["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]

        # Step 2: Get the latest videos from the uploads playlist
        video_ids = []
        next_page_token = None

        while len(videos) < min_results:
            playlist_items = youtube.playlistItems().list(
                part="contentDetails",
                playlistId=uploads_playlist_id,
                maxResults=max_results
            ).execute()
            if next_page_token:
                playlist_items = youtube.playlistItems().list(
                    part="contentDetails",
                    playlistId=uploads_playlist_id,
                    maxResults=max_results,
                    pageToken=next_page_token
                ).execute()

            video_ids = [item["contentDetails"]["videoId"] for item in playlist_items["items"]]

            # Step 3: Get statistics for each video
            video_response = youtube.videos().list(
                part="contentDetails,statistics,snippet,player,liveStreamingDetails",
                id=",".join(video_ids)
            ).execute()

            for video in video_response["items"]:
                live_details = video.get("liveStreamingDetails")
                title = video["snippet"]["title"]
                duration = isodate.parse_duration(video["contentDetails"]["duration"]).total_seconds()
                vertical = is_vertical(video["player"]["embedHtml"])
                video_id = video["id"]
                stats = video["statistics"]
                DaysAndHoursdifference = (now - datetime.strptime(video["snippet"]["publishedAt"], "%Y-%m-%dT%H:%M:%SZ")).total_seconds() // 3600

                if DaysAndHoursdifference > 72 and duration > 60 and not vertical and live_details is None:
                    videos.append({
                        "title": title,
                        "video_id": video_id,
                        "publishedAt": video["snippet"]["publishedAt"],
                        "live_details": live_details,
                        "views": stats.get("viewCount", "0"),
                        "likes": stats.get("likeCount", "0"),
                        "comments": stats.get("commentCount", "0"),
                        "HoursSinceUpload": DaysAndHoursdifference
                    })
                    # Stop if we have enough
                    if len(videos) >= min_results:
                        return videos

            # Check for next page
            next_page_token = playlist_items.get("nextPageToken")
            if not next_page_token:
                break  # No more videos in playlist

            return videos


    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)

def resolve_channel_id_and_name(youtube_url: str):
    """
    Given any YouTube URL, return the canonical channel ID (UC...) and channel name.
    """
    parsed = urlparse(youtube_url)
    path = parsed.path.strip("/")

    channel_id = None

    # Direct channel ID link
    match = re.match(r"channel/(UC[\w-]{22})", path)
    if match:
        channel_id = match.group(1)

    # Handle-based link (@username)
    elif path.startswith("@"):
        handle = path[1:]
        request = youtube.search().list(
            q=handle,
            type="channel",
            part="id"
        )
        response = request.execute()
        if response["items"]:
            channel_id = response["items"][0]["id"]["channelId"]

    # Custom /c/ or /user/ links
    elif path.startswith("c/") or path.startswith("user/"):
        custom_name = path.split("/", 1)[1]
        request = youtube.search().list(
            q=custom_name,
            type="channel",
            part="id"
        )
        response = request.execute()
        if response["items"]:
            channel_id = response["items"][0]["id"]["channelId"]

    # Video link with ab_channel
    elif "watch" in path:
        query = parse_qs(parsed.query)
        if "ab_channel" in query:
            channel_name = query["ab_channel"][0]
            request = youtube.search().list(
                q=channel_name,
                type="channel",
                part="id"
            )
            response = request.execute()
            if response["items"]:
                channel_id = response["items"][0]["id"]["channelId"]

    # If we found a channel ID, get the channel name
    if channel_id:
        request = youtube.channels().list(
            part="snippet",
            id=channel_id
        )
        response = request.execute()
        if response["items"]:
            channel_name = response["items"][0]["snippet"]["title"]
            return channel_id, channel_name

    return None, None

# --- Example usage ---
if __name__ == "__main__":
    YT_API_KEY = APIKey
    sheet = client.open_by_key(sheetID).sheet1
    

# Get all values in the sheet
all_values = sheet.get_all_values()

# Find the index of the "Youtube Links" column
header = all_values[0]  # first row is the header
Channel_index = header.index("Channel")  # find the column position
Name_index = header.index("Name")  # find the column position
AvgViews_index = header.index("Avg Views")  # find the column position
AvgLikes_index = header.index("Avg Likes")  # find the column position
AvgComments_index = header.index("Avg Comments")  # find the column position
EngagementRate_index = header.index("Engagement Rate")  # find the column position


# Loop through each row (skipping header)
for row_num, row in enumerate(all_values[1:], start=2):  # start=2 because row 1 is header
    url = row[Channel_index]
    try:
        channel_id, channel_name = resolve_channel_id_and_name(url)
        if not channel_id:
            raise ValueError("Could not extract channel id from URL")
    except Exception as e:
        sheet.update_cell(row_num, Name_index + 1, "Error: " + str(e))  # Write error message in Name column
        continue

    videos = get_latest_videos(channel_id)
    
    if videos:
        total_views = sum(int(v["views"]) for v in videos)
        total_likes = sum(int(v["likes"]) for v in videos)
        EngagementRate = (total_likes / total_views * 100) if total_views > 0 else 0
        total_comments = sum(int(v["comments"]) for v in videos)
        num_videos = len(videos)
        
        avg_views = math.floor(total_views / num_videos)
        avg_likes = math.floor(total_likes / num_videos)
        avg_comments = math.floor(total_comments / num_videos)

        print(f"Average Views: {avg_views:.2f}")
        print(f"Average Likes: {avg_likes:.2f}")
        print(f"Engagement Rate: {EngagementRate:.2f}%")
        print(f"Average Comments: {avg_comments:.2f}")
        
        
        # Or print each video
        for video in videos:
            print(video)
            print("---")
        

    sheet.update_cell(row_num, Name_index + 1, channel_name)  # Write channel name
    sheet.update_cell(row_num, AvgViews_index + 1, f"{avg_views}")  # Write average views
    sheet.update_cell(row_num, AvgLikes_index + 1, f"{avg_likes}")    # Write average likes
    sheet.update_cell(row_num, AvgComments_index + 1, f"{avg_comments}") # Write average comments
    sheet.update_cell(row_num, EngagementRate_index + 1, f"{EngagementRate:.2f}%")  # Write engagement rate

