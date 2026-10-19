
import asyncio
import os
import json
import logging

from contextlib import asynccontextmanager
from websockets.asyncio.client import connect
from fastapi import FastAPI
import uvicorn


# Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# Xiaozhi MCP URL must be configured in Render Environment Variables
XIAOZHI_MCP_URL = os.environ.get("XIAOZHI_MCP_URL", "")


async def handle_xiaozhi_messages(websocket):
    async for message in websocket:
        try:
            logging.info("Message received from Xiaozhi")

            data = json.loads(message)

            msg_id = data.get("id")
            method = data.get("method")

            # MCP Initialize
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
                            "name": "Xiaozhi MCP Bridge",
                            "version": "1.1.0"
                        }
                    }
                }

                await websocket.send(json.dumps(response))

            # MCP Ping
            elif method == "ping":
                response = {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {}
                }

                await websocket.send(json.dumps(response))

            # No music tools registered
            elif method == "tools/list":
                response = {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {
                        "tools": []
                    }
                }

                await websocket.send(json.dumps(response))

                logging.info(
                    "No tools registered. Music tool calling disabled."
                )

            # Reject any unexpected tool calls
            elif method == "tools/call":
                response = {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "error": {
                        "code": -32601,
                        "message": "No tools are available on this MCP server"
                    }
                }

                await websocket.send(json.dumps(response))

            # Other unsupported methods
            elif msg_id is not None:
                response = {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "error": {
                        "code": -32601,
                        "message": "Method not found"
                    }
                }

                await websocket.send(json.dumps(response))

        except Exception as e:
            logging.error(f"Error handling message: {e}")


async def connect_to_xiaozhi():
    if not XIAOZHI_MCP_URL:
        logging.error(
            "XIAOZHI_MCP_URL is missing. Set it in Render Environment."
        )
        return

    while True:
        try:
            logging.info("Connecting to Xiaozhi MCP WebSocket...")

            async with connect(XIAOZHI_MCP_URL) as websocket:
                logging.info(
                    "Successfully connected to Xiaozhi MCP Server!"
                )

                await handle_xiaozhi_messages(websocket)

        except asyncio.CancelledError:
            raise

        except Exception as e:
            logging.error(f"Connection lost: {e}")
            await asyncio.sleep(5)


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(connect_to_xiaozhi())

    try:
        yield
    finally:
        task.cancel()

        try:
            await task
        except asyncio.CancelledError:
            pass


app = FastAPI(lifespan=lifespan)


@app.get("/")
def read_root():
    return {
        "status": "Xiaozhi MCP Bridge Running",
        "music_tool": "disabled",
        "registered_tools": 0
    }


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port
    )
