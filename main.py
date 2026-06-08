"""Entry point — create world, agents, relationships, and start the server."""

import asyncio
import os
import uvicorn
import random

from config import WORLD_MAP, BUILDINGS, OBJECTS, AGENTS
from world import World
from agent import Agent
from models import Relationship2D, WeightedMemory, Goal, Belief
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
            home_x=cfg.get("home_x"),
            home_y=cfg.get("home_y"),
        )
        agent_map[a.id] = a
        w.agents[a.id] = a

    # Initialize 6D relationships from config
    for cfg in AGENTS:
        a = agent_map[cfg["id"]]
        # Use new 2D relationships if available, else fall back to old format
        rels_2d = cfg.get("init_relationships_2d", {})
        old_rels = cfg.get("init_relationships", {})

        for target_id in set(list(rels_2d.keys()) + list(old_rels.keys())):
            target = agent_map.get(target_id)
            if not target:
                continue

            if target_id in rels_2d:
                rd = rels_2d[target_id]
                rel = Relationship2D(
                    target_id=target_id,
                    target_name=target.name,
                    trust=rd.get("trust", 5),
                    affection=rd.get("affection", 5),
                    respect=rd.get("respect", 5),
                    attraction=rd.get("attraction", 0),
                    jealousy=rd.get("jealousy", 0),
                    resentment=rd.get("resentment", 0),
                )
                if rd.get("memory"):
                    rel.shared_memories.append(rd["memory"])
            else:
                # Old format: single affinity → approximate 6D
                rd_old = old_rels[target_id]
                aff = rd_old.get("affinity", 0)
                # Map affinity (-10..+10) to 6D roughly
                if aff > 5:
                    rel = Relationship2D(target_id, target.name,
                        trust=min(10, 5 + aff * 0.5),
                        affection=min(10, 5 + aff * 0.6),
                        respect=min(10, 5 + aff * 0.4),
                        attraction=max(0, aff - 3) if aff > 5 else 0,
                    )
                elif aff < -1:
                    rel = Relationship2D(target_id, target.name,
                        trust=max(0, 5 + aff * 0.5),
                        affection=max(0, 5 + aff * 0.5),
                        respect=max(0, 5 + aff * 0.3),
                        resentment=min(10, abs(aff)),
                    )
                else:
                    rel = Relationship2D(target_id, target.name,
                        trust=5 + aff * 0.3,
                        affection=5 + aff * 0.3,
                        respect=5 + aff * 0.2,
                    )
                if rd_old.get("memory"):
                    rel.shared_memories.append(rd_old["memory"])

            a.relationships[target_id] = rel

    # Initialize beliefs from config
    for cfg in AGENTS:
        a = agent_map[cfg["id"]]
        for target_id, bd in cfg.get("init_beliefs", {}).items():
            if target_id in agent_map:
                a.beliefs[target_id] = Belief(
                    about_id=target_id,
                    kindness=bd.get("kindness", 5),
                    honesty=bd.get("honesty", 5),
                    competence=bd.get("competence", 5),
                    reliability=bd.get("reliability", 5),
                    confidence=bd.get("confidence"),
                )

    # Initialize weighted memories from config
    for cfg in AGENTS:
        a = agent_map[cfg["id"]]
        for md in cfg.get("init_weighted_memories", []):
            mem = WeightedMemory(
                content=md["content"],
                importance=md.get("importance", 5),
                emotion=md.get("emotion", "calm"),
                related_agents=md.get("related_agents", []),
                unresolved=md.get("unresolved", False),
            )
            a.weighted_memories.append(mem)
            # Also add to legacy memory list for backward compat
            a.memory.append(md["content"])

    # Initialize goals from config
    for cfg in AGENTS:
        a = agent_map[cfg["id"]]
        goals = cfg.get("init_goals", [])
        if goals:
            gd = goals[0]  # First goal is the primary
            a.current_goal = Goal(
                goal_type=gd["type"],
                description=gd["description"],
                target_agent_id=gd.get("target"),
                priority=gd.get("priority", 5),
            )
            a.current_plan = a._derive_plan_from_goal(a.current_goal, w)

    server.agents = agent_map

    # Start agent loops
    for ag in agent_map.values():
        asyncio.create_task(server.agent_loop(ag, w, llm))

    print(f"[OK] {len(agent_map)} agents with 6D relationships ready")
    print(f"[OK] Server starting at http://localhost:8000")

    config = uvicorn.Config(server.app, host="0.0.0.0", port=8000, log_level="info")
    srv = uvicorn.Server(config)
    await srv.serve()


if __name__ == "__main__":
    asyncio.run(main())
