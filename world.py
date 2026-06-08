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
        self.recent_speech = {}  # agent_id -> [{from_id, from_name, text, tick_age}]

        # Day/night cycle: each tick = 30 game-minutes, 24h = 48 ticks
        self.time_of_day = 6.0   # start at 6am (dawn)
        self.day_number = 1
        self.tick_in_day = 0

        # Precompute building collision map
        self._building_tiles = set()
        for b in buildings:
            for dx in range(b["w"]):
                for dy in range(b["h"]):
                    self._building_tiles.add((b["x"] + dx, b["y"] + dy))

    # ═══════════════════════════════════════════════════════════════
    # Day/Night Cycle
    # ═══════════════════════════════════════════════════════════════

    def advance_time(self):
        """Advance game time. Each tick = 30 game-minutes."""
        self.time_of_day += 0.5
        self.tick_in_day += 1
        if self.time_of_day >= 24.0:
            self.time_of_day -= 24.0
            self.day_number += 1
            self.tick_in_day = 0

    def day_phase(self):
        """Return current phase: dawn/day/dusk/night."""
        t = self.time_of_day
        if 5.0 <= t < 7.0:
            return "dawn"
        elif 7.0 <= t < 18.0:
            return "day"
        elif 18.0 <= t < 20.0:
            return "dusk"
        else:
            return "night"

    def is_nighttime(self):
        return self.day_phase() in ("night",)

    def is_sleeping_hours(self):
        """Agents should be home/asleep."""
        t = self.time_of_day
        return t >= 22.0 or t < 5.0

    def time_label(self):
        """Human-readable time string."""
        h = int(self.time_of_day)
        m = int((self.time_of_day - h) * 60)
        phase_emoji = {"dawn": "🌅", "day": "☀️", "dusk": "🌆", "night": "🌙"}
        return f"第{self.day_number}天 {phase_emoji.get(self.day_phase(),'')} {h:02d}:{m:02d}"

    # ═══════════════════════════════════════════════════════════════

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

        # If goal is not walkable (e.g. inside a building), find nearest walkable tile
        if not self.is_walkable(gx, gy):
            best = None
            best_dist = 999
            for dx in range(-3, 4):
                for dy in range(-3, 4):
                    nx, ny = gx + dx, gy + dy
                    if self.is_walkable(nx, ny):
                        d = abs(dx) + abs(dy)
                        if d < best_dist:
                            best_dist = d
                            best = (nx, ny)
            if best:
                gx, gy = best

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

    def random_walkable(self, rng, avoid_agents=True):
        """Return a random walkable tile coordinate, optionally avoiding other agents."""
        import random
        best = None
        for _ in range(200):
            x = rng.randint(0, MAP_WIDTH - 1)
            y = rng.randint(0, MAP_HEIGHT - 1)
            if self.is_walkable(x, y):
                if avoid_agents and self.is_too_close_to_agents(x, y, None, min_dist=2):
                    if best is None:
                        best = (x, y)
                    continue
                return (x, y)
        return best or (MAP_WIDTH // 2, MAP_HEIGHT // 2)

    def get_min_agent_distance(self, x, y, exclude_id=None):
        """Return the minimum Manhattan distance to any other agent."""
        min_dist = 999
        for aid, a in self.agents.items():
            if aid == exclude_id:
                continue
            dist = abs(a.x - x) + abs(a.y - y)
            if dist < min_dist:
                min_dist = dist
        return min_dist

    def is_too_close_to_agents(self, x, y, exclude_id=None, min_dist=3):
        """Check if a tile is too close to other agents."""
        return self.get_min_agent_distance(x, y, exclude_id) < min_dist

    def push_away_from_agents(self, x, y, exclude_id=None, min_dist=3):
        """Try to find a nearby walkable tile that's at least min_dist from others.
        Returns (new_x, new_y) — may return original if no better tile found."""
        best = (x, y)
        best_dist = self.get_min_agent_distance(x, y, exclude_id)
        if best_dist >= min_dist:
            return best

        for dx in range(-3, 4):
            for dy in range(-3, 4):
                nx, ny = x + dx, y + dy
                if not self.is_walkable(nx, ny):
                    continue
                d = self.get_min_agent_distance(nx, ny, exclude_id)
                if d > best_dist:
                    best_dist = d
                    best = (nx, ny)
        return best

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
                # Ensure name is present (use id as fallback)
                entry = {**b, "distance": dist}
                if "type" not in entry:
                    entry["type"] = "building"
                if "name" not in entry:
                    entry["name"] = b.get("id", "房子")
                result.append(entry)
        return result

    def add_event(self, event):
        self.events.append(event)
        if len(self.events) > 100:
            self.events = self.events[-50:]

    def spread_gossip(self, speaker_id, listener_id, about_name, text):
        """Speaker tells listener something about 'about_name'.
        Uses credibility system: effect = source_trust × plausibility × rel_strength."""
        # Resolve about_id
        about_id = None
        for aid, a in self.agents.items():
            if a.name == about_name:
                about_id = aid
                break
        if not about_id:
            speaker = self.agents.get(speaker_id)
            if speaker:
                for rid, rel in speaker.relationships.items():
                    if rel.target_name == about_name:
                        about_id = rid
                        break

        # Determine valence from text and speaker's mood
        speaker_agent = self.agents.get(speaker_id)
        valence = 0
        if speaker_agent:
            dom = speaker_agent.mood.dominate()
            if dom in ('anger', 'sadness'):
                valence = -2
            elif dom in ('happiness',):
                valence = 2
            else:
                positive = ['好', '善良', '可靠', '厉害', '有趣', '喜欢', '棒', '信任']
                negative = ['坏', '讨厌', '烦', '自私', '骗', '懒', '奇怪', '不']
                pos = sum(1 for w in positive if w in text)
                neg = sum(1 for w in negative if w in text)
                valence = (pos - neg) * 1.5

        # Compute credibility
        credibility = self._evaluate_claim_credibility(
            listener_id, speaker_id, about_id, valence, text)

        entry = {
            "speaker": speaker_agent.name if speaker_agent else "?",
            "listener_id": listener_id,
            "about_name": about_name,
            "about_id": about_id,
            "valence": valence,
            "credibility": round(credibility, 2),
            "text": text,
        }
        self.gossip_log.append(entry)
        if len(self.gossip_log) > 50:
            self.gossip_log = self.gossip_log[-30:]

        # Gossip affects the listener
        if about_id and listener_id in self.agents:
            listener = self.agents[listener_id]
            listener.hear_gossip(about_id, about_name, valence, text,
                                source_id=speaker_id)

        # Check relationship stage changes
        if speaker_id in self.agents:
            speaker = self.agents[speaker_id]
            for rid in [listener_id, about_id]:
                if rid and rid in speaker.relationships:
                    rel = speaker.relationships[rid]
                    stage = rel.stage()
                    # Broadcast as event if significant
                    if stage.value in ('romantic_interest', 'lover', 'enemy'):
                        self.add_event({
                            "type": "relationship_milestone",
                            "agent_id": speaker_id,
                            "agent_name": speaker.name,
                            "target_id": rid,
                            "target_name": rel.target_name,
                            "stage": stage.value,
                            "stage_label": stage.label(),
                            "stage_emoji": stage.emoji(),
                        })

        return entry

    def _evaluate_claim_credibility(self, listener_id, speaker_id, about_id,
                                     valence, text):
        """Compute how credible a gossip claim is to the listener.
        Returns 0-1 credibility score."""
        listener = self.agents.get(listener_id)
        if not listener:
            return 0.3

        # 1. Source trust: how much does listener trust the speaker?
        source_trust = 0.3  # default for strangers
        if speaker_id and speaker_id in listener.relationships:
            source_trust = listener.relationships[speaker_id].trust / 10.0

        # 2. Claim plausibility: does this match what listener believes?
        claim_plausibility = 0.5
        if about_id and about_id in listener.beliefs:
            belief = listener.beliefs[about_id]
            if valence < 0:
                # Negative claim: less plausible if listener believes target is kind/honest
                kindness_conf = belief.confidence.get('kindness', 0.3)
                if belief.kindness > 7 and kindness_conf > 0.5:
                    claim_plausibility = 0.2
                elif belief.kindness > 5:
                    claim_plausibility = 0.4
                else:
                    claim_plausibility = 0.6
            else:
                # Positive claim: less plausible if listener believes target is unkind
                kindness_conf = belief.confidence.get('kindness', 0.3)
                if belief.kindness < 3 and kindness_conf > 0.5:
                    claim_plausibility = 0.25
                elif belief.kindness < 5:
                    claim_plausibility = 0.4
                else:
                    claim_plausibility = 0.65

        # 3. Relationship strength with the subject
        rel_strength = 0.3
        if about_id and about_id in listener.relationships:
            rel = listener.relationships[about_id]
            avg_dim = (rel.trust + rel.affection + rel.respect) / 30.0
            rel_strength = 0.3 + avg_dim * 0.7

        return source_trust * claim_plausibility * rel_strength

    def record_speech_to(self, target_id, from_id, from_name, text):
        """Record that 'from' said something to 'target', so target can respond."""
        if target_id not in self.recent_speech:
            self.recent_speech[target_id] = []
        self.recent_speech[target_id].append({
            "from_id": from_id,
            "from_name": from_name,
            "text": text,
            "tick_age": 0,
        })
        if len(self.recent_speech[target_id]) > 6:
            self.recent_speech[target_id] = self.recent_speech[target_id][-6:]

    def get_recent_speech_for(self, agent_id):
        """Get recent speech directed at this agent, then age and clean up."""
        entries = self.recent_speech.get(agent_id, [])
        # Age entries, remove old ones (>3 ticks)
        fresh = []
        for e in entries:
            e["tick_age"] += 1
            if e["tick_age"] <= 3:
                fresh.append(e)
        self.recent_speech[agent_id] = fresh
        return fresh
