from pyairtable import Api, Table
import requests
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import re
import requests
from googleapiclient.discovery import build
from urllib.parse import urlparse, parse_qs
import sys
from datetime import datetime
import isodate
import math
import json

with open("config.json") as f:
    config = json.load(f)

now = datetime.now()
APIKey = config["youtube"]["api_key"]

# Define the scope
scope = [
    'https://www.googleapis.com/auth/spreadsheets',
    "https://www.googleapis.com/auth/drive"
]

# Add credentials
youtube = build("youtube", "v3", developerKey=APIKey)
api_key = config["airtable"]["api_key"]
base_id = config["airtable"]["base_id"]
table_name = config["airtable"]["table_name"]
api = Api(api_key)

headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json" 
}


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
            part="contentDetails,statistics",
            id=channel_id
        ).execute()

        if not channel_response["items"]:
            print("Channel not found.")
            return None

        uploads_playlist_id = channel_response["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
        subscriber_count = channel_response["items"][0]["statistics"]["subscriberCount"]

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
                        "HoursSinceUpload": DaysAndHoursdifference,
                        "subscriberCount": subscriber_count
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

# Create a Table instance
try:
    table = api.table(base_id, table_name)
    records = table.all()
    #print(records)
    #breakpoint()
    if records:
        YTLink_column = 'Youtube Link'
        ChannelName_column = 'Channel Name'
        Subscribers_column = 'Subscribers'
        AvgViews_column = 'Avg Views'
        AvgLikes_column = 'Avg Likes'
        AvgComments_column = 'Avg Comments'
        EngagementRate_column = 'Engagement Rate'

        
        # Get all values from the first column
        first_column_values = [record['fields'].get(YTLink_column) for record in records]
        #print(f"Values in first column: {first_column_values}")
        
        # Or loop through each record
        for record in records:
            record_id = record['id']
            fields = record['fields']
            if fields:
                first_value = fields.get(YTLink_column)
                
                # Skip if no YouTube link or empty field
                if not first_value:
                    print(f"Skipping record {record_id}: No YouTube link provided")
                    continue
                
                # Validate it's a YouTube URL
                if not ('youtube.com' in first_value.lower() or 'youtu.be' in first_value.lower()):
                    table.update(record_id, {ChannelName_column: f"Skipping record {record_id}: Invalid YouTube URL - {first_value}"})
                    print(f"Skipping record {record_id}: Invalid YouTube URL - {first_value}")
                    continue
                
                try:
                    # Try to resolve channel ID and name
                    channel_id, channel_name = resolve_channel_id_and_name(first_value)
                    
                    # Skip if channel not found
                    if not channel_id or not channel_name:
                        table.update(record_id, {ChannelName_column: f"Skipping record {record_id}: Could not resolve channel from {first_value}"})
                        print(f"Skipping record {record_id}: Could not resolve channel from {first_value}")
                        continue
                    
                    # Get channel stats
                    Channel_Stats = get_latest_videos(channel_id)
                    
                    # Skip if no videos found
                    if not Channel_Stats:
                        table.update(record_id, {ChannelName_column: f"Skipping record {record_id}: No valid videos found for {channel_name}"})
                        print(f"Skipping record {record_id}: No valid videos found for {channel_name}")
                        continue

                    Subscribers = int(Channel_Stats[0]["subscriberCount"])
                    total_views = sum(int(v["views"]) for v in Channel_Stats)  
                    total_likes = sum(int(v["likes"]) for v in Channel_Stats)
                    EngagementRate = (total_likes / total_views) if total_views > 0 else 0
                    total_comments = sum(int(v["comments"]) for v in Channel_Stats)
                    num_videos = len(Channel_Stats)
            
                    avg_views = math.floor(total_views / num_videos)
                    avg_likes = math.floor(total_likes / num_videos)
                    avg_comments = math.floor(total_comments / num_videos)

                    """print(f"Channel Name: {channel_name}")
                    print(f"Average Views: {avg_views:.2f}")
                    print(f"Average Likes: {avg_likes:.2f}")
                    print(f"Engagement Rate: {EngagementRate:.2f}%")
                    print(f"Average Comments: {avg_comments:.2f}")

                    for video in Channel_Stats:
                        print(video)
                        print("---")"""
                    
                    
                    update_fields = {
                        ChannelName_column: channel_name,
                        Subscribers_column: Subscribers,
                        AvgViews_column: avg_views,
                        AvgLikes_column: avg_likes,
                        AvgComments_column: avg_comments,
                        EngagementRate_column: EngagementRate
                    }
                    
                    # Single update call instead of 6 separate calls
                    table.update(record_id, update_fields)
                
                except Exception as e:
                    print(f"Error processing record {record_id}: {e}")
                    continue  # Move to next record

except Exception as e:
    print(f"Error: {e}")
