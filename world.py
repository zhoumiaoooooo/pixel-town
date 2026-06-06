"""World grid, pathfinding, and state management."""

from collections import deque
from config import GRASS, WATER, STONE, BRIDGE, MAP_WIDTH, MAP_HEIGHT, TILE_SIZE

DIRS = [(0, -1), (1, 0), (0, 1), (-1, 0)]


class World:
    def __init__(self, grid, buildings, objects_):
        self.grid = grid
        self.buildings = buildings
        self.objects = objects_
        self.agents = {}
        self.events = []
        self.gossip_log = []  # track all gossip spread

        # Precompute building collision map
        self._building_tiles = set()
        for b in buildings:
            for dx in range(b["w"]):
                for dy in range(b["h"]):
                    self._building_tiles.add((b["x"] + dx, b["y"] + dy))

    def is_walkable(self, x, y):
        """Check if a tile coordinate is walkable."""
        if not (0 <= x < MAP_WIDTH and 0 <= y < MAP_HEIGHT):
            return False
        tile = self.grid[y][x]
        if tile == WATER:
            return False
        if (x, y) in self._building_tiles:
            return False
        return True

    def bfs_path(self, start, goal, max_steps=30):
        """BFS from start to goal (tile coords). Returns list of (x,y) steps excluding start."""
        sx, sy = int(start[0]), int(start[1])
        gx, gy = int(goal[0]), int(goal[1])

        if (sx, sy) == (gx, gy):
            return []

        visited = {(sx, sy)}
        parent = {}
        q = deque([(sx, sy)])

        while q:
            cx, cy = q.popleft()
            if (cx, cy) == (gx, gy):
                break
            if len(parent) >= max_steps * 4:
                continue
            for dx, dy in DIRS:
                nx, ny = cx + dx, cy + dy
                if (nx, ny) not in visited and self.is_walkable(nx, ny):
                    visited.add((nx, ny))
                    parent[(nx, ny)] = (cx, cy)
                    q.append((nx, ny))

        if (gx, gy) not in parent:
            # No full path — return partial toward goal
            best = min(
                visited,
                key=lambda p: abs(p[0] - gx) + abs(p[1] - gy),
                default=None,
            )
            if best is None or best == (sx, sy):
                return []
            # Reconstruct to best
            path = []
            cur = best
            while cur in parent:
                path.append(cur)
                cur = parent[cur]
                if cur == (sx, sy):
                    break
            path.reverse()
            return path

        # Reconstruct path
        path = []
        cur = (gx, gy)
        while cur in parent:
            path.append(cur)
            cur = parent[cur]
            if cur == (sx, sy):
                break
        path.reverse()
        return path[:max_steps]

    def random_walkable(self, rng):
        """Return a random walkable tile coordinate."""
        import random
        for _ in range(200):
            x = rng.randint(0, MAP_WIDTH - 1)
            y = rng.randint(0, MAP_HEIGHT - 1)
            if self.is_walkable(x, y):
                return (x, y)
        return (MAP_WIDTH // 2, MAP_HEIGHT // 2)

    def get_nearby_agents(self, agent_id, x, y, radius=6):
        """Return list of nearby agent dicts (excluding self)."""
        result = []
        for aid, a in self.agents.items():
            if aid == agent_id:
                continue
            dist = abs(a.x - x) + abs(a.y - y)
            if dist <= radius:
                result.append({
                    "id": aid,
                    "name": a.name,
                    "role": a.role,
                    "x": a.x, "y": a.y,
                    "distance": dist,
                })
        return result

    def get_nearby_objects(self, x, y, radius=4):
        """Return nearby world objects."""
        result = []
        for obj in self.objects:
            dist = abs(obj["x"] - x) + abs(obj["y"] - y)
            if dist <= radius:
                result.append({**obj, "distance": dist})
        for b in self.buildings:
            cx, cy = b["x"] + b["w"] // 2, b["y"] + b["h"] // 2
            dist = abs(cx - x) + abs(cy - y)
            if dist <= radius + 2:
                result.append({**b, "distance": dist, "type": b.get("type", "building")})
        return result

    def add_event(self, event):
        self.events.append(event)
        if len(self.events) > 100:
            self.events = self.events[-50:]

    def spread_gossip(self, speaker_id, listener_id, about_name, text):
        """Speaker tells listener something about 'about_name'. Affects listener's view."""
        # Try to find which agent 'about_name' refers to
        about_id = None
        for aid, a in self.agents.items():
            if a.name == about_name:
                about_id = aid
                break
        if not about_id:
            # Check if about_name is in speaker's relationships
            speaker = self.agents.get(speaker_id)
            if speaker:
                for rid, rel in speaker.relationships.items():
                    if rel.target_name == about_name:
                        about_id = rid
                        break

        # Determine valence from text and speaker's emotion
        speaker_agent = self.agents.get(speaker_id)
        valence = 0
        if speaker_agent:
            if speaker_agent.emotion.type in ('angry', 'hurt'):
                valence = -2
            elif speaker_agent.emotion.type in ('happy', 'grateful', 'excited'):
                valence = 2
            else:
                # keyword heuristic
                positive = ['好', '善良', '可靠', '厉害', '有趣', '喜欢', '棒', '信任']
                negative = ['坏', '讨厌', '烦', '自私', '骗', '懒', '奇怪', '不']
                pos = sum(1 for w in positive if w in text)
                neg = sum(1 for w in negative if w in text)
                valence = (pos - neg) * 1.5

        entry = {
            "speaker": speaker_agent.name if speaker_agent else "?",
            "listener_id": listener_id,
            "about_name": about_name,
            "about_id": about_id,
            "valence": valence,
            "text": text,
        }
        self.gossip_log.append(entry)
        if len(self.gossip_log) > 50:
            self.gossip_log = self.gossip_log[-30:]

        # Gossip affects the listener's relationship with the subject
        if about_id and listener_id in self.agents:
            listener = self.agents[listener_id]
            listener.hear_gossip(about_id, about_name, valence, text)

        return entry
