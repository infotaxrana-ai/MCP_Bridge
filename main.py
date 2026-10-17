import asyncio
import os
import sys
import json
import logging
import requests
from websockets.asyncio.client import connect
from fastapi import FastAPI
import uvicorn
import threading

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

app = FastAPI()

@app.get("/")
def read_root():
    return {"status": "Xiaozhi MCP Bridge Running"}

# Xiaozhi MCP WebSocket URL
XIAOZHI_MCP_URL = os.environ.get(
    "XIAOZHI_MCP_URL",
    "wss://api.xiaozhi.me/mcp/?token=eyJhbGciOiJFUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VySWQiOjEwMzIwNzcsImFnZW50SWQiOjI0OTc5NTgsImVuZHBvaW50SWQiOiJhZ2VudF8yNDk3OTU4IiwicHVycG9zZSI6Im1jcC1lbmRwb2ludCIsImlhdCI6MTc5MjI1ODU2NSwiZXhwIjoxODIzODE2MTY1fQ.AaALZ4noyh4EjoOYqGT6ldIztdm5gj5E1BXFiLuueWkqTxnwewCnyslel9E4CUsXb5AsivZOP2RFE4MTjYgfHA"
)

# আপনার Render-এ চলা YT-Player সার্ভিসের URL
YT_PLAYER_URL = os.environ.get("YT_PLAYER_URL", "https://yt-player-m0wo.onrender.com")

def search_youtube_audio(query):
    """yt-player service-এ রিকোয়েস্ট পাঠিয়ে অডিও লিঙ্ক উদ্ধার করা"""
    try:
        response = requests.get(f"{YT_PLAYER_URL}/play", params={"song": query}, timeout=15)
        if response.status_code == 200:
            data = response.json()
            return data.get("url") or data.get("stream_url") or data.get("audio_url")
        else:
            logging.error(f"YT-Player returned status code: {response.status_code}")
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
                        "capabilities": {
                            "tools": {}
                        },
                        "serverInfo": {
                            "name": "Xiaozhi Music MCP Bridge",
                            "version": "1.0.0"
                        }
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
                    
                    if audio_url:
                        result_text = f"Playing {song_name}: {audio_url}"
                    else:
                        result_text = f"Sorry, could not find audio for {song_name}"
                        
                    response = {
                        "jsonrpc": "2.0",
                        "id": msg_id,
                        "result": {
                            "content": [
                                {
                                    "type": "text",
                                    "text": result_text
                                }
                            ]
                        }
                    }
                    await websocket.send(json.dumps(response))
                    logging.info(f"Sent song result to Xiaozhi: {result_text}")

        except json.JSONDecodeError:
            logging.error("Failed to decode JSON message")
        except Exception as e:
            logging.error(f"Error handling message: {e}")

async def connect_to_xiaozhi():
    while True:
        try:
            logging.info("Xiaozhi MCP WebSocket-e connect hobar chesta kora hocche...")
            async with connect(XIAOZHI_MCP_URL) as websocket:
                logging.info("Successfully connected to Xiaozhi MCP Server!")
                await handle_xiaozhi_messages(websocket)
                
        except Exception as e:
            logging.error(f"Connection disconnect hoye geche: {e}")
            await asyncio.sleep(5)

def run_websocket():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(connect_to_xiaozhi())

if __name__ == "__main__":
    t = threading.Thread(target=run_websocket, daemon=True)
    t.start()
    
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)
