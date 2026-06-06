"""Agent class — personality, perception, decision, action, memory."""

import asyncio
import random


class Agent:
    def __init__(self, agent_id, name, x, y, personality, role, color, backstory="", rng=None):
        self.id = agent_id
        self.name = name
        self.x = x
        self.y = y
        self.personality = personality  # dict with O,C,E,A,N (0-1)
        self.role = role
        self.color = color
        self.backstory = backstory
        self.current_goal = "认识小镇上的每一个人"
        self.memory = []
        self.relationships = {}  # agent_id -> affinity (-1 to 1)
        self.path = []  # current movement path
        self.rng = rng or random.Random()
        self._target_obj = None  # name of target to move toward
        self._idle_ticks = 0

    def perceive(self, world):
        """Gather everything the agent can sense right now."""
        return {
            "nearby_agents": world.get_nearby_agents(self.id, self.x, self.y, radius=6),
            "nearby_objects": world.get_nearby_objects(self.x, self.y, radius=5),
        }

    async def tick(self, world, llm_client):
        """One full decision-action cycle."""
        perception = self.perceive(world)

        # Build state dict for LLM
        state = {
            "name": self.name,
            "role": self.role,
            "x": self.x, "y": self.y,
            "personality": self.personality,
            "backstory": self.backstory,
            "current_goal": self.current_goal,
            "memory": self.memory,
        }

        action = await llm_client.decide(state, perception)
        return await self._execute(action, world, perception)

    async def _execute(self, action, world, perception):
        """Execute the action and return an event dict for broadcasting."""
        action_type = action.get("action", "idle")
        target = action.get("target", "")
        text = action.get("text", "")
        thought = action.get("thought", "")

        if action_type == "move":
            target_pos = self._resolve_target(target, world, perception)
            if target_pos:
                self.path = world.bfs_path((self.x, self.y), target_pos, max_steps=20)
                # Take up to 3 steps this tick
                steps = min(len(self.path), 3 + int(self.personality.get("E", 0.5) * 2))
                if steps > 0 and self.path:
                    for _ in range(steps):
                        if self.path:
                            nx, ny = self.path.pop(0)
                            if world.is_walkable(nx, ny):
                                self.x, self.y = nx, ny
                    self._idle_ticks = 0
                    return {
                        "type": "agent_update",
                        "agent_id": self.id,
                        "x": self.x, "y": self.y,
                        "path": self.path,
                        "thought": thought,
                    }
            # Can't reach target — idle instead
            self._idle_ticks += 1
            self._maybe_change_goal(world)
            return {"type": "agent_update", "agent_id": self.id, "x": self.x, "y": self.y, "thought": thought}

        elif action_type == "speak" and text:
            self._idle_ticks = 0
            # Update relationship with target
            nearby = perception.get("nearby_agents", [])
            for a in nearby:
                if a["name"] == target:
                    rel = self.relationships.get(a["id"], 0)
                    self.relationships[a["id"]] = min(1.0, rel + 0.05)
                    break
            self.memory.append(f"我对{target}说: {text}")
            if len(self.memory) > 10:
                self.memory = self.memory[-10:]
            return {
                "type": "speech",
                "agent_id": self.id,
                "agent_name": self.name,
                "text": text,
                "target": target,
                "thought": thought,
            }

        elif action_type == "interact":
            self._idle_ticks = 0
            obj_name = target or "周围的东西"
            self.memory.append(f"我在{obj_name}这里互动了一下")
            if len(self.memory) > 10:
                self.memory = self.memory[-10:]
            return {
                "type": "interaction",
                "agent_id": self.id,
                "agent_name": self.name,
                "target": obj_name,
                "thought": thought,
            }

        else:  # idle
            self._idle_ticks += 1
            self._maybe_change_goal(world)
            return {
                "type": "agent_idle",
                "agent_id": self.id,
                "x": self.x, "y": self.y,
                "thought": thought,
            }

    def _resolve_target(self, target_name, world, perception):
        """Convert a target name/description to (x,y) tile coordinates."""
        if not target_name:
            return None

        target_lower = target_name.lower().strip()

        # Check nearby agents by name
        for a in perception.get("nearby_agents", []):
            if a["name"] in target_name:
                return (a["x"], a["y"])

        # Check nearby objects
        for obj in perception.get("nearby_objects", []):
            obj_name = obj.get("name", "")
            obj_type = obj.get("type", "")
            if obj_name and target_name in obj_name:
                return (obj["x"] + obj.get("w", 1) // 2, obj["y"] + obj.get("h", 1) // 2)
            if obj_type and obj_type in target_lower:
                return (obj["x"] + obj.get("w", 1) // 2, obj["y"] + obj.get("h", 1) // 2)

        # Check all buildings by name
        for b in world.buildings:
            if b.get("name") and target_name in b["name"]:
                return (b["x"] + b["w"] // 2, b["y"] + b["h"] // 2)

        # Check all objects by name/type
        for obj in world.objects:
            obj_name = obj.get("name", "")
            obj_type = obj.get("type", "")
            if obj_name and target_name in obj_name:
                return (obj["x"], obj["y"])
            if obj_type and obj_type in target_lower:
                return (obj["x"], obj["y"])

        # Fallback: random nearby walkable tile in general direction
        if "四处" in target_name or "逛逛" in target_name or "走走" in target_name:
            return world.random_walkable(self.rng)

        return None

    def _maybe_change_goal(self, world):
        """After too many idle ticks, pick a new goal."""
        if self._idle_ticks > 3:
            self.current_goal = self.rng.choice([
                "去篝火旁看看",
                "去集市逛逛",
                "在水井边休息一下",
                "找个长椅坐坐",
                "去朋友家串门",
                "随便走走",
            ])
            self._idle_ticks = 0

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "role": self.role,
            "x": self.x, "y": self.y,
            "color": self.color,
            "personality": self.personality,
            "backstory": self.backstory,
            "current_goal": self.current_goal,
            "memory": self.memory,
            "relationships": self.relationships,
        }
