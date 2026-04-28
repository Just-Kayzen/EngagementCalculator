import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import re
import requests
from googleapiclient.discovery import build

credsPath = r"C:\Python\EngagementCalculator\engagementcalculator-fef079d955ba.json"
sheetID = r"1_SMHZEbGrT8MmSgH7hFLA9DuQ2zbf3i5GMREYh3ZnDM"
APIKey = r"AIzaSyC6vbLan_c0K2sAL8RBqV9F21ssSaXsRuc"

# Define the scope
scope = [
    'https://www.googleapis.com/auth/spreadsheets',
    "https://www.googleapis.com/auth/drive"
]

# --- Helpers ---
def extract_video_id(url: str) -> str:
    patterns = [
        r"(?:v=|\/v\/|youtu\.be\/|\/embed\/)([A-Za-z0-9_-]{11})",
        r"([A-Za-z0-9_-]{11})$"
    ]
    for p in patterns:
        m = re.search(p, url)
        if m:
            return m.group(1)
    raise ValueError("Could not extract video id from URL")

# --- Official YouTube Data API (views, likes, comments) ---
def get_youtube_stats(api_key: str, video_url: str) -> dict:
    video_id = extract_video_id(video_url)
    youtube = build("youtube", "v3", developerKey=api_key)
    resp = youtube.videos().list(part="statistics,snippet", id=video_id).execute()
    items = resp.get("items", [])
    if not items:
        raise ValueError("Video not found or API quota exceeded")
    stats = items[0].get("statistics", {})
    return {
        "video_id": video_id,
        "title": items[0].get("snippet", {}).get("title", ""),
        "views": int(stats.get("viewCount", 0)),
        "likes": int(stats.get("likeCount", 0)),
        "comments": int(stats.get("commentCount", 0))
    }

def like_rate(views, likes):
    if views == 0:
        return 0
    return round(likes / views * 100, 2)

def comment_rate(views, comments):
    if views == 0:
        return 0
    return round(comments / views * 100, 2)

# Add credentials
creds = Credentials.from_service_account_file(credsPath, scopes=scope)
# Authenticate and create the client
client = gspread.authorize(creds)


# --- Example usage ---
if __name__ == "__main__":
    YT_API_KEY = APIKey
    sheet = client.open_by_key(sheetID).sheet1

# Get all values in the sheet
all_values = sheet.get_all_values()

# Find the index of the "Youtube Links" column
header = all_values[0]  # first row is the header
YTLink_index = header.index("Youtube Links")  # find the column position
Title_index = header.index("Title")  # find the column position
Views_index = header.index("Views")  # find the column position
Likes_index = header.index("Likes")  # find the column position
Comments_index = header.index("Comments")  # find the column position
LikeRate_index = header.index("Like Rate")  # find the column position
CommentRate_index = header.index("Comment Rate")  # find the column position


# Loop through each row (skipping header)
for row_num, row in enumerate(all_values[1:], start=2):  # start=2 because row 1 is header
    url = row[YTLink_index]
    try:
        stats = get_youtube_stats(YT_API_KEY, url)
    except ValueError as e:
        sheet.update_cell(row_num, Title_index + 1, "Error: " + str(e))  # Write error message in Title column
        continue
    LikeRate = like_rate(stats["views"], stats["likes"])
    CommentRate = comment_rate(stats["views"], stats["comments"])
    sheet.update_cell(row_num, Title_index + 1, stats["title"])  # Write title
    sheet.update_cell(row_num, Views_index + 1, stats["views"])  # Write views
    sheet.update_cell(row_num, Likes_index + 1, stats["likes"])    # Write likes
    sheet.update_cell(row_num, Comments_index + 1, stats["comments"]) # Write comments
    sheet.update_cell(row_num, LikeRate_index + 1, LikeRate)  # Write like rate
    sheet.update_cell(row_num, CommentRate_index + 1, CommentRate)  # Write comment rate

    #print("Official stats:", stats)

