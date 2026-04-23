import re
from googleapiclient.discovery import build

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


# --- Example usage ---
if __name__ == "__main__":
    YT_API_KEY = "YOUR_YOUTUBE_API_KEY"
    url = "https://www.youtube.com/watch?v=jNQXAC9IVRw"
    stats = get_youtube_stats(YT_API_KEY, url)
    print("Official stats:", stats)
    dislikes = get_dislikes_return_yd(url)
    print("Estimated dislikes (third-party):", dislikes)
