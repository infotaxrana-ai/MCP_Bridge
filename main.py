import asyncio
import os
import sys
import json
import logging
from websockets.asyncio.client import connect
from fastapi import FastAPI
import uvicorn
import threading

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Render Web Service-এর Port Detection-এর জন্য Dummy HTTP App
app = FastAPI()

@app.get("/")
def read_root():
    return {"status": "Xiaozhi MCP Bridge Running"}

# আপনার আপডেট করা নতুন Xiaozhi MCP WebSocket URL
XIAOZHI_MCP_URL = os.environ.get(
    "XIAOZHI_MCP_URL",
    "wss://api.xiaozhi.me/mcp/?token=eyJhbGciOiJFUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VySWQiOjEwMzIwNzcsImFnZW50SWQiOjI0OTc5NTgsImVuZHBvaW50SWQiOiJhZ2VudF8yNDk3OTU4IiwicHVycG9zZSI6Im1jcC1lbmRwb2ludCIsImlhdCI6MTc5MjI1NzAxMCwiZXhwIjoxODIzODE0NjEwfQ.rqZTk9FZoxvkXbuUeJ6uaYxDBRZ2AruLbo0sRdOMxXzzu4kUMZ9EAhVXBIMGFd-_26HnJCWxdwXzjWnRNjzXHA"
)

async def handle_xiaozhi_messages(websocket):
    async for message in websocket:
        try:
            logging.info(f"Message received from Xiaozhi: {message}")
            data = json.loads(message)
            
            msg_id = data.get("id")
            method = data.get("method")
            
            # Xiaozhi Protocol Handshake Response
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
                response = {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {}
                }
                await websocket.send(json.dumps(response))
                logging.info("Sent ping response to Xiaozhi")
                
            elif method == "notifications/initialized":
                pass

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
            logging.info("5 second por abar reconnect kora hobe...")
            await asyncio.sleep(5)

def run_websocket():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(connect_to_xiaozhi())

if __name__ == "__main__":
    # WebSocket Client-কে আলাদা ব্যাকগ্রাউন্ড থ্রেডে চালনা করা
    t = threading.Thread(target=run_websocket, daemon=True)
    t.start()
    
    # Render-এর Port Check সম্পন্ন করার জন্য Uvicorn চালু করা
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)
