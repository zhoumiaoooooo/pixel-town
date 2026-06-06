"""Entry point — create world, agents, relationships, and start the server."""

import asyncio
import os
import uvicorn
import random

from config import WORLD_MAP, BUILDINGS, OBJECTS, AGENTS
from world import World
from agent import Agent, Relationship
from llm import DeepSeekClient, LLMClient, MockLLMClient
import server


async def main():
    w = World(WORLD_MAP, BUILDINGS, OBJECTS)
    server.world = w

    # Choose LLM: DeepSeek API → Ollama → Mock
    api_key = os.environ.get("DEEPSEEK_API_KEY", "")
    if api_key:
        llm = DeepSeekClient(api_key=api_key)
        print("[OK] DeepSeek API connected (deepseek-chat)")
    else:
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
            print("[WARN] No DEEPSEEK_API_KEY or Ollama, using MockLLMClient")
            print("[TIP]  Set $env:DEEPSEEK_API_KEY = 'sk-...' for real AI")

    server.llm_client = llm

    # Create agents
    agent_map = {}
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
        agent_map[a.id] = a
        w.agents[a.id] = a

    # Initialize relationships from config
    for cfg in AGENTS:
        a = agent_map[cfg["id"]]
        for target_id, rel_data in cfg.get("init_relationships", {}).items():
            target = agent_map.get(target_id)
            if target:
                rel = Relationship(target_id, target.name, affinity=rel_data["affinity"])
                for tag in rel_data.get("tags", []):
                    rel.tags.add(tag)
                if rel_data.get("memory"):
                    rel.shared_memories.append(rel_data["memory"])
                a.relationships[target_id] = rel

    server.agents = agent_map

    # Start agent loops
    for a in agent_map.values():
        asyncio.create_task(server.agent_loop(a, w, llm))

    print(f"[OK] {len(agent_map)} agents with relationships ready")
    print(f"[OK] Server starting at http://localhost:8000")

    config = uvicorn.Config(server.app, host="0.0.0.0", port=8000, log_level="info")
    srv = uvicorn.Server(config)
    await srv.serve()


if __name__ == "__main__":
    asyncio.run(main())
