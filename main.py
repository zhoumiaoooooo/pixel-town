"""Entry point — create world, agents, and start the server."""

import asyncio
import uvicorn
import random

from config import WORLD_MAP, BUILDINGS, OBJECTS, AGENTS
from world import World
from agent import Agent
from llm import LLMClient, MockLLMClient
import server


async def main():
    # Create world
    w = World(WORLD_MAP, BUILDINGS, OBJECTS)
    server.world = w

    # Choose LLM client
    try:
        import httpx
        async with httpx.AsyncClient(timeout=2.0) as c:
            resp = await c.get("http://localhost:11434/api/tags")
            if resp.status_code == 200:
                llm = LLMClient()
                print("[OK] Ollama connected, using LLMClient")
            else:
                raise Exception("Ollama not available")
    except Exception:
        llm = MockLLMClient()
        print("[WARN] Ollama not available, using MockLLMClient (random behavior)")

    server.llm_client = llm

    # Create agents
    for cfg in AGENTS:
        a = Agent(
            agent_id=cfg["id"],
            name=cfg["name"],
            x=cfg["x"], y=cfg["y"],
            personality=cfg["personality"],
            role=cfg["role"],
            color=cfg["color"],
            backstory=cfg["backstory"],
            rng=random.Random(cfg["id"].__hash__()),
        )
        server.agents[a.id] = a
        w.agents[a.id] = a

    # Start agent loops as background tasks
    for a in server.agents.values():
        asyncio.create_task(server.agent_loop(a, w, llm))

    print(f"[OK] {len(server.agents)} agents ready")
    print(f"[OK] Server starting at http://localhost:8000")

    # Start uvicorn
    config = uvicorn.Config(server.app, host="0.0.0.0", port=8000, log_level="info")
    srv = uvicorn.Server(config)
    await srv.serve()


if __name__ == "__main__":
    asyncio.run(main())
