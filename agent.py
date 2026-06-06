"""Agent — Needs, Emotion, Relationship, Memory, Decision."""

import time
import random


class Needs:
    """Four decaying needs that drive behavior."""
    __slots__ = ('hunger', 'social', 'rest', 'purpose')

    def __init__(self):
        self.hunger = 80 + random.uniform(-10, 10)
        self.social = 80 + random.uniform(-10, 10)
        self.rest = 80 + random.uniform(-10, 10)
        self.purpose = 80 + random.uniform(-10, 10)

    def decay(self, dt=1.0):
        rates = {'hunger': 1.5, 'social': 3, 'rest': 1.5, 'purpose': 1.0}
        self.hunger = max(0, min(100, self.hunger - rates['hunger'] * dt))
        self.social = max(0, min(100, self.social - rates['social'] * dt))
        self.rest = max(0, min(100, self.rest - rates['rest'] * dt))
        self.purpose = max(0, min(100, self.purpose - rates['purpose'] * dt))

    def lowest(self):
        d = {'hunger': self.hunger, 'social': self.social, 'rest': self.rest, 'purpose': self.purpose}
        return min(d, key=d.get)

    def replenish(self, need, amount):
        current = getattr(self, need, 100)
        setattr(self, need, min(100, current + amount))

    def summary(self):
        return f"饥饿{self.hunger:.0f} 社交{self.social:.0f} 疲劳{self.rest:.0f} 意义{self.purpose:.0f}"


EMOTIONS = ['happy', 'sad', 'angry', 'anxious', 'calm', 'excited', 'lonely', 'grateful', 'hurt', 'curious']
EMOJI = {
    'happy': '😊', 'sad': '😢', 'angry': '😠', 'anxious': '😰',
    'calm': '😌', 'excited': '😆', 'lonely': '🥺', 'grateful': '🙏',
    'hurt': '💔', 'curious': '🤔',
}

class Emotion:
    """Current emotional state — triggered by events, decays over time."""
    __slots__ = ('type', 'intensity', 'history')

    def __init__(self):
        self.type = 'calm'
        self.intensity = 3.0
        self.history = []  # last few emotions

    def feel(self, emotion_type, strength, reason=""):
        """Trigger an emotion."""
        if emotion_type in EMOTIONS:
            self.type = emotion_type
            self.intensity = min(10.0, max(0.0, strength))
            self.history.append((emotion_type, reason, time.time()))
            if len(self.history) > 20:
                self.history = self.history[-10:]

    def decay(self, dt=1.0):
        """Drift back toward calm."""
        if self.type == 'calm':
            self.intensity = max(1.0, self.intensity - 0.3 * dt)
        else:
            self.intensity = max(0.0, self.intensity - 1.2 * dt)
            if self.intensity < 1.0:
                self.type = 'calm'
                self.intensity = 2.0

    def emoji(self):
        return EMOJI.get(self.type, '😶')

    def summary(self):
        if self.type == 'calm' and self.intensity < 3:
            return "平静"
        return f"{EMOJI.get(self.type,'')}{self.type}({self.intensity:.0f}/10)"


class Relationship:
    """Rich relationship between two agents."""
    __slots__ = ('target_id', 'target_name', 'affinity', 'tags', 'shared_memories', 'last_interaction')

    def __init__(self, target_id, target_name, affinity=0.0):
        self.target_id = target_id
        self.target_name = target_name
        self.affinity = affinity  # -10 to +10
        self.tags = set()
        self.shared_memories = []
        self.last_interaction = 0

    def modify(self, delta, tag=None, memory=None):
        self.affinity = max(-10, min(10, self.affinity + delta))
        if tag:
            if delta > 0:
                self.tags.discard(tag.lstrip('-'))
                self.tags.add(tag)
            else:
                self.tags.add(tag)
        if memory:
            self.shared_memories.append(memory)
            if len(self.shared_memories) > 8:
                self.shared_memories = self.shared_memories[-8:]
        self.last_interaction = time.time()

    def summary(self):
        valence = "😍" if self.affinity > 5 else "🙂" if self.affinity > 1 else "😐" if self.affinity > -1 else "😒" if self.affinity > -5 else "😡"
        tags_str = ",".join(self.tags) if self.tags else ""
        return f"{valence}{self.target_name}({self.affinity:+.0f}) [{tags_str}]"


class Agent:
    def __init__(self, agent_id, name, x, y, personality, role, color, backstory="", rng=None):
        self.id = agent_id
        self.name = name
        self.x = x
        self.y = y
        self.personality = personality
        self.role = role
        self.color = color
        self.backstory = backstory
        self.current_goal = "认识小镇上的每一个人"
        self.memory = []
        self.relationships = {}  # target_id -> Relationship
        self.path = []
        self.rng = rng or random.Random()
        self._idle_ticks = 0

        # New systems
        self.needs = Needs()
        self.emotion = Emotion()
        self.gossip_heard = []  # recent gossip heard

    def perceive(self, world):
        return {
            "nearby_agents": world.get_nearby_agents(self.id, self.x, self.y, radius=6),
            "nearby_objects": world.get_nearby_objects(self.x, self.y, radius=5),
        }

    async def tick(self, world, llm_client):
        """One full cycle: decay → perceive → decide → act."""
        self.needs.decay()
        self.emotion.decay()

        # auto-emotion from needs
        lowest = self.needs.lowest()
        if self.needs.social < 20 and self.emotion.type == 'calm':
            self.emotion.feel('lonely', 6 - self.needs.social / 5, "社交需求很低")
        elif self.needs.rest < 15:
            self.emotion.feel('anxious', 7, "太累了")
        elif self.needs.hunger < 15:
            self.emotion.feel('anxious', 5, "饿了")

        perception = self.perceive(world)

        state = {
            "name": self.name, "role": self.role,
            "x": self.x, "y": self.y,
            "personality": self.personality,
            "backstory": self.backstory,
            "current_goal": self.current_goal,
            "memory": self.memory,
            "needs": {
                "hunger": self.needs.hunger, "social": self.needs.social,
                "rest": self.needs.rest, "purpose": self.needs.purpose,
                "lowest": lowest,
            },
            "emotion": self.emotion.summary(),
            "relationships": [r.summary() for r in self.relationships.values()],
            "gossip_heard": self.gossip_heard[-3:],
        }

        action = await llm_client.decide(state, perception)
        return await self._execute(action, world, perception)

    async def _execute(self, action, world, perception):
        action_type = action.get("action", "idle")
        target = action.get("target", "")
        text = action.get("text", "")
        thought = action.get("thought", "")
        gossip_about = action.get("gossip_about", "")  # who they're talking about

        if action_type == "move":
            target_pos = self._resolve_target(target, world, perception)
            if target_pos:
                self.path = world.bfs_path((self.x, self.y), target_pos, max_steps=20)
                steps = min(len(self.path), 3 + int(self.personality.get("E", 0.5) * 2))
                if steps > 0 and self.path:
                    for _ in range(steps):
                        if self.path:
                            nx, ny = self.path.pop(0)
                            if world.is_walkable(nx, ny):
                                self.x, self.y = nx, ny
                    self._idle_ticks = 0
                    return {
                        "type": "agent_update", "agent_id": self.id,
                        "x": self.x, "y": self.y, "path": self.path,
                        "thought": thought,
                        "emotion": self.emotion.summary(),
                        "emoji": self.emotion.emoji(),
                        "needs": self.needs.summary(),
                    }
            self._idle_ticks += 1
            self._maybe_change_goal(world)
            return {
                "type": "agent_update", "agent_id": self.id,
                "x": self.x, "y": self.y, "thought": thought,
                "emotion": self.emotion.summary(),
                "emoji": self.emotion.emoji(),
                "needs": self.needs.summary(),
            }

        elif action_type == "speak" and text:
            self._idle_ticks = 0
            self.needs.replenish('social', 15)
            # Find target agent
            nearby = perception.get("nearby_agents", [])
            target_id = None
            for a in nearby:
                if a["name"] == target:
                    target_id = a["id"]
                    break

            # Update relationship with speaker's feelings
            if target_id:
                rel = self.relationships.get(target_id)
                if not rel:
                    rel = Relationship(target_id, target)
                    self.relationships[target_id] = rel
                # determine tone from emotion
                delta = 0.1
                tag = None
                if self.emotion.type in ('grateful', 'happy', 'excited'):
                    delta = 0.5; tag = "好感"
                elif self.emotion.type in ('angry', 'hurt'):
                    delta = -0.8; tag = "不满"
                elif self.emotion.type == 'lonely':
                    delta = 0.3; tag = "倾诉"
                rel.modify(delta, tag, f"我说: {text[:20]}")

            # Handle gossip
            gossip_event = None
            if gossip_about and target_id:
                gossip_event = world.spread_gossip(self.id, target_id, gossip_about, text)

            self.memory.append(f"我对{target}说: {text}")
            if len(self.memory) > 10:
                self.memory = self.memory[-10:]

            # Feel good after socializing
            self.emotion.feel('happy', 5, f"和{target}聊了天")

            return {
                "type": "speech", "agent_id": self.id,
                "agent_name": self.name, "text": text,
                "target": target, "thought": thought,
                "emotion": self.emotion.summary(),
                "emoji": self.emotion.emoji(),
                "gossip_about": gossip_about,
                "gossip_event": gossip_event,
            }

        elif action_type == "interact":
            self._idle_ticks = 0
            obj_name = target or "周围的东西"

            # replenish needs based on object
            if "篝火" in obj_name or "火" in obj_name:
                self.needs.replenish('social', 10)
                self.needs.replenish('purpose', 8)
                self.emotion.feel('calm', 6, "在篝火旁取暖")
            elif "水井" in obj_name or "井" in obj_name:
                self.needs.replenish('hunger', 15)
                self.emotion.feel('calm', 4, "喝水休息")
            elif "长椅" in obj_name or "椅" in obj_name:
                self.needs.replenish('rest', 30)
                self.emotion.feel('calm', 7, "坐着休息")
            elif "集市" in obj_name:
                self.needs.replenish('hunger', 20)
                self.needs.replenish('purpose', 10)
                self.emotion.feel('excited', 5, "逛集市")
            elif "家" in obj_name:
                self.needs.replenish('rest', 40)
                self.needs.replenish('purpose', 5)
                self.emotion.feel('calm', 8, "回到家了")
            else:
                self.needs.replenish('purpose', 5)

            self.memory.append(f"我在{obj_name}这里互动了一下")
            if len(self.memory) > 10:
                self.memory = self.memory[-10:]

            return {
                "type": "interaction", "agent_id": self.id,
                "agent_name": self.name, "target": obj_name,
                "thought": thought,
                "emotion": self.emotion.summary(),
                "emoji": self.emotion.emoji(),
            }

        else:  # idle
            self._idle_ticks += 1
            self.needs.replenish('rest', 8)
            self._maybe_change_goal(world)
            return {
                "type": "agent_idle", "agent_id": self.id,
                "x": self.x, "y": self.y, "thought": thought,
                "emotion": self.emotion.summary(),
                "emoji": self.emotion.emoji(),
                "needs": self.needs.summary(),
            }

    def feel(self, emotion_type, strength, reason=""):
        self.emotion.feel(emotion_type, strength, reason)

    def hear_gossip(self, about_id, about_name, valence, content):
        """Receive gossip about someone — affects relationship with that person."""
        self.gossip_heard.append(f"{about_name}: {content}")
        if len(self.gossip_heard) > 10:
            self.gossip_heard = self.gossip_heard[-10:]

        if about_id == self.id:
            # Gossip about me!
            if valence < 0:
                self.emotion.feel('hurt', abs(valence) * 2, f"听说有人在说我坏话")
            else:
                self.emotion.feel('grateful', valence * 2, f"听说有人在夸我")

        rel = self.relationships.get(about_id)
        if not rel:
            rel = Relationship(about_id, about_name)
            self.relationships[about_id] = rel
        rel.modify(valence * 0.3, "听闻" if valence > 0 else "负面传闻", f"听说: {content[:20]}")

    def _resolve_target(self, target_name, world, perception):
        if not target_name:
            return None

        for a in perception.get("nearby_agents", []):
            if a["name"] in target_name:
                return (a["x"], a["y"])

        for obj in perception.get("nearby_objects", []):
            obj_name = obj.get("name", "")
            obj_type = obj.get("type", "")
            if obj_name and target_name in obj_name:
                return (obj["x"] + obj.get("w", 1) // 2, obj["y"] + obj.get("h", 1) // 2)
            if obj_type and obj_type in target_name.lower():
                return (obj["x"] + obj.get("w", 1) // 2, obj["y"] + obj.get("h", 1) // 2)

        for b in world.buildings:
            if b.get("name") and target_name in b["name"]:
                return (b["x"] + b["w"] // 2, b["y"] + b["h"] // 2)

        for obj in world.objects:
            if obj.get("name") and target_name in obj["name"]:
                return (obj["x"], obj["y"])
            if obj.get("type") and obj["type"] in target_name.lower():
                return (obj["x"], obj["y"])

        if "四处" in target_name or "走走" in target_name:
            return world.random_walkable(self.rng)

        return None

    def _maybe_change_goal(self, world):
        if self._idle_ticks > 3:
            lowest = self.needs.lowest()
            goals = {
                'hunger': ["去集市找点吃的", "去水井喝水"],
                'social': ["找人聊聊天", "去篝火旁看看有人没"],
                'rest': ["找个长椅坐坐", "回家休息"],
                'purpose': ["去集市逛逛看看新鲜事", "去篝火旁唱歌"],
            }
            self.current_goal = self.rng.choice(goals.get(lowest, ["随便走走"]))
            self._idle_ticks = 0

    def to_dict(self):
        return {
            "id": self.id, "name": self.name, "role": self.role,
            "x": self.x, "y": self.y, "color": self.color,
            "personality": self.personality,
            "backstory": self.backstory,
            "current_goal": self.current_goal,
            "memory": self.memory,
            "emotion": {"type": self.emotion.type, "intensity": self.emotion.intensity, "emoji": self.emotion.emoji()},
            "needs": {"hunger": self.needs.hunger, "social": self.needs.social, "rest": self.needs.rest, "purpose": self.needs.purpose},
            "relationships": {rid: {"name": r.target_name, "affinity": r.affinity, "tags": list(r.tags), "memories": r.shared_memories[-3:]} for rid, r in self.relationships.items()},
            "gossip_heard": self.gossip_heard[-5:],
        }
