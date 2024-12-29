import asyncio

from playwright.async_api import async_playwright
from playwright.sync_api import sync_playwright


def scrape_video_details(video_url: str) -> dict:
    """
    Scrape YouTube video title, views, and top 5 comments.

    :param video_url: URL of the YouTube video.
    :return: Dictionary containing video title, views, and top comments.
    """
    with sync_playwright() as p:
        print("Launching Bright Data Scraping Browser...")
        browser = p.chromium.connect_over_cdp(
            "wss://brd-customer-hl_9654ded4-zone-scrapperyoutube:9zq91c2voiql@brd.superproxy.io:9222"
        )
        page = browser.new_page()

        print(f"Navigating to video URL: {video_url}")
        page.goto(video_url)


        # Wait for the page to fully load

        page.screenshot(path="screenshot.png")
        print("Screenshot saved for debugging.")


        # Extract title
        try:
            print("Extracting video title...")
            page.wait_for_selector("div#title.style-scope h1 yt-formatted-string")
            title_element = page.query_selector("div#title.style-scope h1 yt-formatted-string")
            title = title_element.inner_text() if title_element else "Title not found"
            print(f"Video Title: {title}")
        except Exception as e:
            print(f"Failed to extract title: {e}")
            title = "Unknown Title"


        # Extract channel name
        try:
            print("Extracting channel name...")
            channel_name_element = page.query_selector("div#upload-info ytd-channel-name #text")
            channel_name = channel_name_element.inner_text().strip() if channel_name_element else "Unknown Channel"
            print(f"Channel Name: {channel_name}")
        except Exception as e:
            print(f"Failed to extract channel name: {e}")
            channel_name = "Unknown Channel"

        # Extract view count
        try:
            print("Extracting video views...")
            view_count_element = page.query_selector("span.view-count")
            views = view_count_element.inner_text().strip() if view_count_element else "Unknown Views"
            print(f"Video Views: {views}")
        except Exception as e:
            print(f"Failed to extract views: {e}")
            views = "Unknown Views"

        # Extract top 5 comments
        try:
            print("Extracting top 5 comments...")
            page.evaluate("window.scrollBy(0, 1000)")  # Scroll to the comment section
            page.wait_for_selector("ytd-comment-thread-renderer", timeout=60000)
            comment_elements = page.query_selector_all("ytd-comment-thread-renderer")[:5]
            comments = []

            for comment_element in comment_elements:
                comment_text_element = comment_element.query_selector("#content-text")
                comment_text = comment_text_element.inner_text().strip() if comment_text_element else "Comment not found"
                comments.append(comment_text)
                print(f"Comment: {comment_text}")
        except Exception as e:
            print(f"Failed to extract comments: {e}")
            comments = []

        # Close the browser
        print("Closing browser...")
        browser.close()

        # Return data in JSON format
        result = {
            "title": title,
            "views": views,
            "comments": [{"comment": comment} for comment in comments],
        }
        print("Scraping completed. Result:", result)
        return result


async def scrape_youtube_live(url, websocket):
    try:
        async with async_playwright() as p:
            # First try with Bright Data proxy
            try:
                browser = await p.chromium.connect_over_cdp(
                    "wss://brd-customer-hl_9654ded4-zone-scrapperyoutube:9zq91c2voiql@brd.superproxy.io:9222"
                )
                context = browser.contexts[0]
            except Exception as proxy_error:
                print(f"Bright Data proxy connection failed: {proxy_error}")
                # Fallback to regular headless browser
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context()

            page = await context.new_page()
            await page.goto(url)

            # Extract Title
            try:
                title = await page.locator("h1.title.style-scope.ytd-video-primary-info-renderer").inner_text()
                print(f"Title: {title}")
            except Exception:
                title = "Unknown Title"

            # Extract Channel Name
            try:
                channel_name = await page.locator("#upload-info #channel-name").inner_text()
                print(f"Channel Name: {channel_name}")
            except Exception:
                channel_name = "Unknown Channel"

            # Function to Fetch Live Comments
            async def fetch_live_comments():
                try:
                    comment_elements = await page.frame_locator("iframe#chatframe").locator(
                        "yt-live-chat-text-message-renderer #message"
                    ).all()
                    return [await comment.inner_text() for comment in comment_elements]
                except Exception as e:
                    print(f"Failed to extract live comments: {e}")
                    return []

            # Initial Live Comments Fetch
            live_comments = await fetch_live_comments()
            await websocket.send_json({
                "title": title,
                "channel_name": channel_name,
                "live_comments": live_comments,
            })

            # Poll for Live Comments
            while True:
                try:
                    live_comments = await fetch_live_comments()
                    if live_comments:  # Only send if we have comments
                        await websocket.send_json({"live_comments": live_comments})
                    await asyncio.sleep(30)
                except Exception as e:
                    print(f"Error during comment polling: {e}")
                    await websocket.send_json({"error": "Comment polling failed, attempting to reconnect..."})
                    await asyncio.sleep(5)  # Wait before retrying

    except Exception as e:
        print(f"Scraping error: {e}")
        await websocket.send_json({"error": f"Scraping failed: {str(e)}"})
    finally:
        if 'browser' in locals():
            await browser.close()
