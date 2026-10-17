import asyncio
import os
import sys
import json
import logging
import requests
from contextlib import asynccontextmanager
from websockets.asyncio.client import connect
from fastapi import FastAPI
import uvicorn

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

XIAOZHI_MCP_URL = os.environ.get(
    "XIAOZHI_MCP_URL",
    "wss://api.xiaozhi.me/mcp/?token=eyJhbGciOiJFUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VySWQiOjEwMzIwNzcsImFnZW50SWQiOjI0OTc5NTgsImVuZHBvaW50SWQiOiJhZ2VudF8yNDk3OTU4IiwicHVycG9zZSI6Im1jcC1lbmRwb2ludCIsImlhdCI6MTc5MjI1OTIzNCwiZXhwIjoxODIzODE2ODM0fQ.3s6TbeNkN_Q09nEfJiEWYbtc3ZHdbByYWD6KRhNiFkabksbRfOdIUVqWkVnv7NSsNpDZb9KU1MpeDENB75C_Ug"
)

YT_PLAYER_URL = os.environ.get("YT_PLAYER_URL", "https://yt-player-m0wo.onrender.com")

def search_youtube_audio(query):
    try:
        response = requests.get(f"{YT_PLAYER_URL}/play", params={"song": query}, timeout=15)
        if response.status_code == 200:
            data = response.json()
            return data.get("url") or data.get("stream_url") or data.get("audio_url")
    except Exception as e:
        logging.error(f"Error fetching audio from yt-player: {e}")
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
                                "description": "Play or search a song from YouTube",
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
                logging.info("Sent tools list to Xiaozhi")
                
            elif method == "tools/call":
                params = data.get("params", {})
                tool_name = params.get("name")
                arguments = params.get("arguments", {})
                
                if tool_name == "play_music":
                    song_name = arguments.get("song_name", "")
                    logging.info(f"Xiaozhi requested song: {song_name}")
                    
                    audio_url = search_youtube_audio(song_name)
                    result_text = f"Playing {song_name}: {audio_url}" if audio_url else f"Sorry, could not find audio for {song_name}"
                        
                    response = {
                        "jsonrpc": "2.0",
                        "id": msg_id,
                        "result": {
                            "content": [{"type": "text", "text": result_text}]
                        }
                    }
                    await websocket.send(json.dumps(response))
                    logging.info(f"Sent song result to Xiaozhi: {result_text}")

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
    # Background-e WebSocket loop shuru korbe server start howar sathe sathe
    asyncio.create_task(connect_to_xiaozhi())
    yield

app = FastAPI(lifespan=lifespan)

@app.get("/")
def read_root():
    return {"status": "Xiaozhi MCP Bridge Running"}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)
