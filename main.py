import asyncio
import os
import sys
import logging
from websockets.asyncio.client import connect

# Logging setup
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Xiaozhi MCP WebSocket URL with Token
XIAOZHI_MCP_URL = os.environ.get(
    "XIAOZHI_MCP_URL",
    "wss://api.xiaozhi.me/mcp/?token=eyJhbGciOiJFUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VySWQiOjEwMzIwNzcsImFnZW50SWQiOjI0OTc5NTgsImVuZHBvaW50SWQiOiJhZ2VudF8yNDk3OTU4IiwicHVycG9zZSI6Im1jcC1lbmRwb2ludCIsImlhdCI6MTc5MjI1NzAxMCwiZXhwIjoxODIzODE0NjEwfQ.rqZTk9FZoxvkXbuUeJ6uaYxDBRZ2AruLbo0sRdOMxXzzu4kUMZ9EAhVXBIMGFd-_26HnJCWxdwXzjWnRNjzXHA"
)

async def connect_to_xiaozhi():
    while True:
        try:
            logging.info("Xiaozhi MCP WebSocket-e connect hobar chesta kora hocche...")
            async with connect(XIAOZHI_MCP_URL) as websocket:
                logging.info("Successfully connected to Xiaozhi MCP Server!")
                
                async for message in websocket:
                    logging.info(f"Message received from Xiaozhi: {message}")
                    # Xiaozhi theke request ashle ekhane handle hobe
                    
        except Exception as e:
            logging.error(f"Connection disconnect hoye geche: {e}")
            logging.info("5 second por abar reconnect kora hobe...")
            await asyncio.sleep(5)

if __name__ == "__main__":
    try:
        asyncio.run(connect_to_xiaozhi())
    except KeyboardInterrupt:
        logging.info("Server বন্ধ করা হয়েছে।")
