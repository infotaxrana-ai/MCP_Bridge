import asyncio
import os
import sys
import json
import logging
import urllib.parse
from contextlib import asynccontextmanager
from websockets.asyncio.client import connect
from fastapi import FastAPI
import uvicorn

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

XIAOZHI_MCP_URL = os.environ.get(
    "XIAOZHI_MCP_URL",
    "wss://api.xiaozhi.me/mcp/?token=eyJhbGciOiJFUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VySWQiOjEwMzIwNzcsImFnZW50SWQiOjI0OTc5NTgsImVuZHBvaW50SWQiOiJhZ2VudF8yNDk3OTU4IiwicHVycG9zZSI6Im1jcC1lbmRwb2ludCIsImlhdCI6MTc5MjI2MDIwOSwiZXhwIjoxODIzODE3ODA5fQ.7KZPdba8W4V3F9Dns8NYVbdosoLxIoDsNzsEwl42ygnDulFZzQa2iKNX8Yqvad-6tJoaqyTRPXkDsmoi3YtrXw"
)

YDLS_SERVER_URL = os.environ.get("YT_PLAYER_URL", "https://ydls.onrender.com")

def generate_ydls_stream_url(youtube_url_or_query):
    try:
        if "youtube.com" not in youtube_url_or_query and "youtu.be" not in youtube_url_or_query:
            search_query = f"ytsearch1:{youtube_url_or_query}"
            encoded_query = urllib.parse.quote(search_query)
            stream_url = f"{YDLS_SERVER_URL}/mp3/{encoded_query}"
        else:
            stream_url = f"{YDLS_SERVER_URL}/mp3/{youtube_url_or_query}"
            
        logging.info(f"Generated YDLS Stream URL: {stream_url}")
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
                logging.info("Sent initialize response to Xiaozhi")
                
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
                                            "description": "Name of the song or specific YouTube video link"
                                        }
                                    },
                                    "required": ["song_name"]
                                }
                            }
                        ]
                    }
                }
                await websocket.send(json.dumps(response))
                logging.info("Sent tools list to Xiaozhi")
                
            elif method == "tools/call":
                params = data.get("params", {})
                tool_name = params.get("name")
                arguments = params.get("arguments", {})
                
                if tool_name in ["play_music", "search_youtube_audio"]:
                    song_name = arguments.get("song_name", "")
                    logging.info(f"Xiaozhi requested song: {song_name}")
                    
                    audio_url = generate_ydls_stream_url(song_name)
                    
                    # 🌟 পরিবর্তন: Xiaozhi স্পিকারের জন্য অডিও অবজেক্ট ফরম্যাটে রেসপন্স পাঠানো
                    if audio_url:
                        response = {
                            "jsonrpc": "2.0",
                            "id": msg_id,
                            "result": {
                                "content": [
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
                                "content": [{"type": "text", "text": f"Sorry, could not stream {song_name}"}]
                            }
                        }
                        
                    await websocket.send(json.dumps(response))
                    logging.info(f"Sent structured audio response to Xiaozhi for: {song_name}")

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
