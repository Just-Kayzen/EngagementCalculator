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

now = datetime.now()
credsPath = r"C:\Python\EngagementCalculator\engagementcalculator-fef079d955ba.json"
sheetID = r"1PsHh67ZCFtPR7fLmIlHJ5iOSQXqfWiq6ocwek289x_4"
APIKey = r"AIzaSyC6vbLan_c0K2sAL8RBqV9F21ssSaXsRuc"

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
    sheet = client.open_by_key(sheetID).sheet1
    
    # Get all values in the sheet
    all_values = sheet.get_all_values()

    # Find the index of the columns
    header = all_values[0]  # first row is the header
    Channel_index = header.index("Channel")  # find the column position
    Name_index = header.index("Name")  # find the column position

    # Loop through each row (skipping header)
    for row_num, row in enumerate(all_values[1:], start=2):  # start=2 because row 1 is header
        url = row[Channel_index]
        try:
            cid, cname = resolve_channel_id_and_name(url)
            print(url, "->", cid, cname)

        except Exception as e:
            print(f"Error processing row {row_num}: {e}", file=sys.stderr)