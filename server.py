"""FastAPI server with WebSocket for real-time agent simulation."""

import asyncio
import json
from fastapi import FastAPI, WebSocket
from fastapi.staticfiles import StaticFiles
from pathlib import Path

app = FastAPI(title="Pixel Town Sim")

# Global state — set by main.py
world = None
agents = {}
llm_client = None
paused = False
tick_speed = 12.0  # seconds between ticks per agent
connected_clients = set()


async def broadcast(msg):
    """Send a JSON message to all connected WebSocket clients."""
    global connected_clients
    dead = set()
    data = json.dumps(msg, ensure_ascii=False)
    for ws in connected_clients:
        try:
            await ws.send_text(data)
        except Exception:
            dead.add(ws)
    connected_clients -= dead


async def agent_loop(agent, world_obj, llm):
    """Async loop for a single agent — runs one tick every tick_speed seconds."""
    await asyncio.sleep(agent.rng.uniform(0, 2))  # stagger start
    while True:
        if not paused:
            try:
                event = await agent.tick(world_obj, llm)
                # Advance game time after each agent tick
                world_obj.advance_time()
                # Attach agent info + time to event for frontend
                event["color"] = agent.color
                event["name"] = agent.name
                event["time_of_day"] = world_obj.time_of_day
                event["day_phase"] = world_obj.day_phase()
                event["day_number"] = world_obj.day_number
                event["time_label"] = world_obj.time_label()
                await broadcast(event)
            except Exception as e:
                import traceback
                print(f"[Agent {agent.name} error] {e}")
                traceback.print_exc()
        await asyncio.sleep(tick_speed)


@app.websocket("/ws")
async def ws_endpoint(websocket: WebSocket):
    global paused, tick_speed
    await websocket.accept()
    connected_clients.add(websocket)

    # Send initial world state
    await websocket.send_text(json.dumps({
        "type": "world_init",
        "map": world.grid,
        "buildings": world.buildings,
        "objects": world.objects,
        "agents": [a.to_dict() for a in agents.values()],
        "tick_speed": tick_speed,
        "paused": paused,
        "time_of_day": world.time_of_day,
        "day_phase": world.day_phase(),
        "day_number": world.day_number,
        "time_label": world.time_label(),
    }, ensure_ascii=False))

    try:
        while True:
            raw = await websocket.receive_text()
            msg = json.loads(raw)
            msg_type = msg.get("type")

            if msg_type == "click_agent":
                agent_id = msg.get("agent_id")
                if agent_id in agents:
                    await websocket.send_text(json.dumps({
                        "type": "agent_detail",
                        "agent": agents[agent_id].to_dict(),
                    }, ensure_ascii=False))

            elif msg_type == "toggle_pause":
                paused = not paused
                await broadcast({"type": "pause_state", "paused": paused})

            elif msg_type == "set_speed":
                tick_speed = max(1.0, float(msg.get("speed", 5.0)))
                await broadcast({"type": "speed_changed", "speed": tick_speed})

    except Exception as e:
        import traceback
        print(f"[WS error] {e}")
        traceback.print_exc()
    finally:
        connected_clients.discard(websocket)


# Mount static files AFTER all routes
static_dir = Path(__file__).parent / "static"
static_dir.mkdir(exist_ok=True)
app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")
