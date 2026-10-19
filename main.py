import asyncio
import os
import sys
import json
import logging
import urllib.parse
import re
import requests
from contextlib import asynccontextmanager
from websockets.asyncio.client import connect
from fastapi import FastAPI
import uvicorn

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

XIAOZHI_MCP_URL = os.environ.get(
    "XIAOZHI_MCP_URL",
    "wss://api.xiaozhi.me/mcp/?token=eyJhbGciOiJFUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VySWQiOjEwMzIwNzcsImFnZW50SWQiOjI0OTc5NTgsImVuZHBvaW50SWQiOiJhZ2VudF8yNDk3OTU4IiwicHVycG9zZ賽e1pY3AtZW5kcG9pbnQiLCJpYXQiOjE3OTIyNjAyMDksImV4cCI6MTgyMzgxNzgwOX0.7KZPdba8W4V3F9Dns8NYVbdosoLxIoDsNzsEwl42ygnDulFZzQa2iKNX8Yqvad-6tJoaqyTRPXkDsmoi3YtrXw"
)

# আপনার লাইভ হওয়া wader/ydls সার্ভারের URL
YDLS_SERVER_URL = os.environ.get("YT_PLAYER_URL", "https://onrender.com")

def get_direct_youtube_link(query):
    """
    কোনো লাইব্রেরি ছাড়া সরাসরি ইউটিউব অফিশিয়াল সার্চ রেজাল্ট থেকে ১ সেকেন্ডে ক্লিন ভিডিও আইডি বের করে।
    """
    try:
        logging.info(f"Scraping YouTube directly for query: {query}")
        encoded_query = urllib.parse.quote(query)
        search_url = f"https://youtube.com{encoded_query}"
        
        # ইউটিউবকে সাধারণ ব্রাউজার হিসেবে রিকোয়েস্ট পাঠানো
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
        response = requests.get(search_url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            # রেগুলার এক্সপ্রেশন দিয়ে প্রথম ভিডিও আইডি (/watch?v=XXXX) খুঁজে বের করা
            video_ids = re.findall(r"watch\?v=(\S{11})", response.text)
            if video_ids:
                video_url = f"https://youtube.com{video_ids[0]}"
                logging.info(f"Successfully scraped YouTube URL: {video_url}")
                return video_url
    except Exception as e:
        logging.error(f"Direct YouTube scrape error: {e}")
    return None

def generate_ydls_stream_url(song_name_or_link):
    try:
        if "youtube.com" not in song_name_or_link and "youtu.be" not in song_name_or_link:
            direct_video_url = get_direct_youtube_link(song_name_or_link)
            if not direct_video_url:
                # যদি কোনো কারণে স্ক্র্যাপ ফেল করে, তবে সেফটি মেথড হিসেবে ydls এর নিজস্ব সার্চ ট্রাই করবে
                encoded_fallback = urllib.parse.quote(f"ytsearch1:{song_name_or_link}")
                return f"{YDLS_SERVER_URL}/mp3/{encoded_fallback}"
            stream_url = f"{YDLS_SERVER_URL}/mp3/{direct_video_url}"
        else:
            stream_url = f"{YDLS_SERVER_URL}/mp3/{song_name_or_link}"
            
        logging.info(f"Final Stream URL generated for bot: {stream_url}")
        return stream_url
    except Exception as e:
        logging.error(f"Error generating stream URL: {e}")
    return None

async def handle_xiaozhi_messages(websocket):
    async for message in websocket:
        try:
            logging.info(f"Message received from Xiaozhi: {message}")
            data = json.loads(message)
            
            msg_id = data.get("id")
            method = data.get("method")
            
            if method == "initialize":
                response = {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {"tools": {}},
                        "serverInfo": {"name": "Xiaozhi Music MCP Bridge", "version": "1.0.0"}
                    }
                }
                await websocket.send(json.dumps(response))
                
            elif method == "ping":
                await websocket.send(json.dumps({"jsonrpc": "2.0", "id": msg_id, "result": {}}))
                
            elif method == "tools/list":
                response = {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {
                        "tools": [
                            {
                                "name": "play_music",
                                "description": "Plays any song or music from YouTube directly on Xiaozhi bot's speaker.",
                                "inputSchema": {
                                    "type": "object",
                                    "properties": {
                                        "song_name": {
                                            "type": "string",
                                            "description": "Name of the song or keywords to search"
                                        }
                                    },
                                    "required": ["song_name"]
                                }
                            }
                        ]
                    }
                }
                await websocket.send(json.dumps(response))
                
            elif method == "tools/call":
                params = data.get("params", {})
                tool_name = params.get("name")
                arguments = params.get("arguments", {})
                
                if tool_name in ["play_music", "search_youtube_audio"]:
                    song_name = arguments.get("song_name", "")
                    logging.info(f"Xiaozhi requested song: {song_name}")
                    
                    audio_url = generate_ydls_stream_url(song_name)
                    
                    if audio_url:
                        response = {
                            "jsonrpc": "2.0",
                            "id": msg_id,
                            "result": {
                                "content": [
                                    {
                                        "type": "text",
                                        "text": f"অবশ্যই, আমি আপনার জন্য {song_name} গানটি প্লে করছি।"
                                    },
                                    {
                                        "type": "audio", 
                                        "audio": {
                                            "url": audio_url,
                                            "title": song_name
                                        }
                                    }
                                ]
                            }
                        }
                    else:
                        response = {
                            "jsonrpc": "2.0",
                            "id": msg_id,
                            "result": {
                                "content": [{"type": "text", "text": f"দুঃখিত, {song_name} গানটি খুঁজে পাওয়া যায়নি।"}]
                            }
                        }
                        
                    await websocket.send(json.dumps(response))
                    logging.info(f"Sent combined response for: {song_name}")

        except Exception as e:
            logging.error(f"Error handling message: {e}")

async def connect_to_xiaozhi():
    while True:
        try:
            logging.info("Connecting to Xiaozhi MCP WebSocket...")
            async with connect(XIAOZHI_MCP_URL) as websocket:
                logging.info("Successfully connected to Xiaozhi MCP Server!")
                await handle_xiaozhi_messages(websocket)
        except Exception as e:
            logging.error(f"Connection lost: {e}")
            await asyncio.sleep(5)

@asynccontextmanager
async def lifespan(app: FastAPI):
    asyncio.create_task(connect_to_xiaozhi())
    yield

app = FastAPI(lifespan=lifespan)

@app.get("/")
def read_root():
    return {"status": "Xiaozhi MCP Bridge Running"}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)
