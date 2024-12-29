from typing import List, Dict
from fastapi import FastAPI, Query, WebSocket, WebSocketDisconnect, HTTPException
from pydantic import BaseModel
from app.playwright_scraper import scrape_video_details
import asyncio
from playwright.async_api import async_playwright
from app.ai_processing import analyze_sentiment, advanced_sentiment_analysis
import os
import json
from datetime import datetime, timedelta
from collections import Counter
import math

# Directory to Store Sentiment Data
SENTIMENT_DIRECTORY = "./sentiment_data"

if not os.path.exists(SENTIMENT_DIRECTORY):
    os.makedirs(SENTIMENT_DIRECTORY)

# Response Model
class VideoDetails(BaseModel):
    title: str
    views: str
    comments: List[Dict]

# Initialize FastAPI App
app = FastAPI(
    title="YouTube Video Analytics",
    description="API for analyzing YouTube video details and live comments using Bright Data and Playwright",
    version="1.0.0",
)

# Connection Tracking
active_connections = set()
MAX_CONNECTIONS = 3

@app.get("/scrap/video-details", response_model=VideoDetails, tags=["Scraping"])
async def scrape_video_details_endpoint(video_url: str = Query(..., description="YouTube video URL")):
    """
    Scrape YouTube video details (title, views, and top 5 comments).
    """
    try:
        details = scrape_video_details(video_url)
        return details
    except Exception as e:
        return {"error": str(e)}

@app.websocket("/ws/live-analytics")
async def live_analytics_endpoint(websocket: WebSocket):
    if len(active_connections) >= MAX_CONNECTIONS:
        await websocket.close(code=4001, reason="Max concurrent connections limit reached.")
        return

    url = websocket.query_params["url"]
    user_id = websocket.query_params.get("user_id", "default_user")
    user_directory = os.path.join(SENTIMENT_DIRECTORY, user_id)

    if not os.path.exists(user_directory):
        os.makedirs(user_directory)

    connection_start_time = datetime.now()
    active_connections.add(websocket)
    print(f"WebSocket connection received for URL: {url} and User ID: {user_id}")

    try:
        await websocket.accept()

        async with async_playwright() as p:
            browser = await p.chromium.connect_over_cdp(
                "wss://brd-customer-hl_9654ded4-zone-scrapperyoutube:9zq91c2voiql@brd.superproxy.io:9222"
            )
            context = browser.contexts[0]
            page = await context.new_page()
            await page.goto(url)

            # Extract initial details
            title = await page.locator("h1.title.style-scope.ytd-video-primary-info-renderer").inner_text()
            channel_name = await page.locator("#upload-info #channel-name").inner_text()

            async def fetch_live_comments():
                try:
                    comment_elements = await page.frame_locator("iframe#chatframe").locator(
                        "yt-live-chat-text-message-renderer #message"
                    ).all()
                    return [await comment.inner_text() for comment in comment_elements]
                except Exception as e:
                    print(f"Failed to extract live comments: {e}")
                    return []

            async def fetch_likes_and_viewers():
                try:
                    # Extract likes
                    likes = 0
                    try:
                        # Get the likes element
                        likes_selector = await page.query_selector("ytd-menu-renderer.ytd-video-primary-info-renderer yt-formatted-string#text")
                        if likes_selector:
                            likes_text = await likes_selector.inner_text()
                            # Clean up likes text
                            likes = int(''.join(filter(str.isdigit, likes_text.replace('K', '000').replace('M', '000000').replace(',', ''))))
                    except Exception as e:
                        print(f"Failed to extract likes: {e}")

                    # Extract viewer count
                    viewer_count = 0
                    try:
                        # Get the view count element
                        view_selector = await page.query_selector("ytd-video-view-count-renderer")
                        if view_selector:
                            view_text = await view_selector.inner_text()
                            # Extract numbers before "watching now"
                            if "watching now" in view_text.lower():
                                viewer_count = int(''.join(filter(str.isdigit, view_text.split("watching")[0])))
                    except Exception as e:
                        print(f"Failed to extract viewer count: {e}")

                    return {
                        "likes": likes,
                        "viewer_count": viewer_count
                    }
                except Exception as e:
                    print(f"Failed to extract likes or viewer count: {e}")
                    return {"likes": 0, "viewer_count": 0}

            processed_comment_ids = set()
            cluster_id = 0
            total_comments = 0
            start_time = datetime.now()

            while True:
                if (datetime.now() - connection_start_time).total_seconds() > 240:
                    await websocket.send_json({"error": "TIMEOUT: Connection closed after 4 minutes. Please reconnect."})
                    break

                new_comments = await fetch_live_comments()
                likes_and_viewers = await fetch_likes_and_viewers()
                current_time = datetime.now()
                elapsed_minutes = math.floor((current_time - start_time).total_seconds() / 60)

                unique_comments = [comment for comment in new_comments if comment not in processed_comment_ids]
                processed_comment_ids.update(unique_comments)

                if unique_comments:
                    sentiment_data = advanced_sentiment_analysis(unique_comments)
                    cluster_id += 1

                    words = " ".join(unique_comments).split()
                    keywords = Counter(w for w in words if len(w) > 3).most_common(10)

                    total_comments += len(unique_comments)
                    comments_per_minute = len(unique_comments)
                    comments_per_hour = total_comments if elapsed_minutes < 60 else math.floor(total_comments / (elapsed_minutes / 60))
                    engagement_ratio = (total_comments / likes_and_viewers["viewer_count"] * 100) if likes_and_viewers["viewer_count"] > 0 else 0

                    time_range_start = start_time + timedelta(minutes=elapsed_minutes)
                    time_range_end = time_range_start + timedelta(minutes=1)

                    cluster_data = {
                        "channel_name": channel_name,
                        "title": title,
                        "cluster_id": cluster_id,
                        "timestamp": current_time.strftime("%Y-%m-%d_%H-%M-%S"),
                        "time_range": {
                            "start": time_range_start.strftime("%H:%M"),
                            "end": time_range_end.strftime("%H:%M"),
                        },
                        "comments": unique_comments,
                        "average_sentiment": sentiment_data["average_sentiment"],
                        "sentiments": sentiment_data["sentiments"],
                        "keywords": [{"keyword": kw, "count": count} for kw, count in keywords],
                        "engagement": {
                            "comments_per_minute": comments_per_minute,
                            "comments_per_hour": comments_per_hour,
                            "total_comments": total_comments,
                            "likes": likes_and_viewers["likes"],
                            "viewer_count": likes_and_viewers["viewer_count"],
                            "engagement_ratio": engagement_ratio
                        },
                    }

                    file_path = os.path.join(user_directory, f"cluster_{cluster_id}_{current_time.strftime('%Y-%m-%d_%H-%M-%S')}.json")
                    with open(file_path, "w") as f:
                        json.dump(cluster_data, f)

                    await websocket.send_json(cluster_data)

                await asyncio.sleep(30)

    except Exception as e:
        print(f"An error occurred: {e}")
        await websocket.send_json({"error": str(e)})

    finally:
        if os.path.exists(user_directory):
            for file_name in os.listdir(user_directory):
                os.remove(os.path.join(user_directory, file_name))
            os.rmdir(user_directory)

        active_connections.remove(websocket)
        await websocket.close()

@app.get("/sentiment/history")
def get_sentiment_history():
    """
    Fetch all historical sentiment data from the directory.
    """
    try:
        all_sentiments = []
        for user_dir in os.listdir(SENTIMENT_DIRECTORY):
            user_path = os.path.join(SENTIMENT_DIRECTORY, user_dir)
            if os.path.isdir(user_path):
                for file_name in sorted(os.listdir(user_path)):
                    file_path = os.path.join(user_path, file_name)
                    with open(file_path, "r") as f:
                        data = json.load(f)
                        all_sentiments.append(data)
        return {"sentiment_history": all_sentiments}
    except Exception as e:
        return {"error": str(e)}
