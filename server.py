import asyncio
import json
import os
from pathlib import Path
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from typing import Set
import uvicorn

app = FastAPI()

# Store the grid state (50x50 = 2500 squares)
# 0 = black, 1 = white
GRID_SIZE = 50
grid_state = [0] * (GRID_SIZE * GRID_SIZE)

# Connected clients
clients: Set[WebSocket] = set()

# Get the directory where server.py is located
BASE_DIR = Path(__file__).resolve().parent

@app.get("/")
async def read_root():
    html_path = BASE_DIR / "index.html"
    return FileResponse(str(html_path))

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    clients.add(websocket)
    print(f"New client connected. Total clients: {len(clients)}")
    
    try:
        # Send current grid state to new client
        await websocket.send_json({
            "type": "init",
            "state": grid_state
        })
        
        # Listen for messages from this client
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            if message["type"] == "update":
                # Update grid state
                index = message["index"]
                value = message["value"]
                
                if 0 <= index < len(grid_state):
                    grid_state[index] = value
                    
                    # Broadcast to all other clients
                    update_message = json.dumps({
                        "type": "update",
                        "index": index,
                        "value": value
                    })
                    
                    # Send to all clients except the sender
                    for client in clients:
                        if client != websocket:
                            try:
                                await client.send_text(update_message)
                            except:
                                pass
                                
            elif message["type"] == "reset":
                # Reset grid
                for i in range(len(grid_state)):
                    grid_state[i] = 0
                
                # Broadcast reset to all clients
                reset_message = json.dumps({"type": "reset"})
                
                for client in clients:
                    try:
                        await client.send_text(reset_message)
                    except:
                        pass
                        
    except WebSocketDisconnect:
        clients.remove(websocket)
        print(f"Client disconnected. Total clients: {len(clients)}")
    except Exception as e:
        print(f"Error: {e}")
        if websocket in clients:
            clients.remove(websocket)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
