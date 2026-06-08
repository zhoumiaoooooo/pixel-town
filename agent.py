"""Agent — Needs, MoodVector, Relationship2D, WeightedMemory, Goal, Belief."""

import time
import random
from models import (
    WeightedMemory, Relationship2D, RelationshipStage,
    Goal, ShortTermPlan, MoodVector, Belief,
    GOAL_TYPES, REL_DIMENSIONS, MOOD_DIMENSIONS, BELIEF_DIMENSIONS,
    BELIEF_LABELS, STAGE_THRESHOLDS,
)


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
        d = {'hunger': self.hunger, 'social': self.social,
             'rest': self.rest, 'purpose': self.purpose}
        return min(d, key=d.get)

    def replenish(self, need, amount):
        current = getattr(self, need, 100)
        setattr(self, need, min(100, current + amount))

    def summary(self):
        return f"饥饿{self.hunger:.0f} 社交{self.social:.0f} 疲劳{self.rest:.0f} 意义{self.purpose:.0f}"

    def to_dict(self):
        return {
            "hunger": round(self.hunger, 1),
            "social": round(self.social, 1),
            "rest": round(self.rest, 1),
            "purpose": round(self.purpose, 1),
        }


class Agent:
    def __init__(self, agent_id, name, x, y, personality, role, color,
                 backstory="", rng=None, home_x=None, home_y=None):
        self.id = agent_id
        self.name = name
        self.x = x
        self.y = y
        self.home_x = home_x if home_x is not None else x
        self.home_y = home_y if home_y is not None else y
        self.personality = personality
        self.role = role
        self.color = color
        self.backstory = backstory
        self.path = []
        self.rng = rng or random.Random()
        self._idle_ticks = 0
        self._tick_count = 0

        # Core systems
        self.needs = Needs()
        self.mood = MoodVector()

        # Multi-dimensional relationships (target_id → Relationship2D)
        self.relationships = {}

        # Beliefs about other agents (target_id → Belief)
        self.beliefs = {}

        # Weighted memory system
        self.weighted_memories = []  # [WeightedMemory]

        # Goal & Plan system
        self.current_goal = None  # Goal
        self.current_plan = None  # ShortTermPlan

        # Gossip tracking
        self.gossip_heard = []

        # Keep backward compat
        self.emotion = self._emotion_proxy()
        self.memory = []

    def _emotion_proxy(self):
        """Backward-compat wrapper — returns legacy emotion dict via property-like access."""

        class EmotionProxy:
            def __init__(self, agent):
                self._agent = agent

            def summary(self):
                return self._agent.mood.mood_label()

            def emoji(self):
                return self._agent.mood.legacy_emotion()["emoji"]

            def to_dict(self):
                return self._agent.mood.legacy_emotion()

        return EmotionProxy(self)

    # ═══════════════════════════════════════════════════════════════
    # Memory System
    # ═══════════════════════════════════════════════════════════════

    def _add_memory(self, content, importance=5, emotion=None,
                    related_agents=None, unresolved=False):
        """Add a weighted memory."""
        mem = WeightedMemory(
            content=content,
            importance=importance,
            emotion=emotion or self.mood.dominate(),
            related_agents=related_agents or [],
            unresolved=unresolved,
        )
        mem.tick_created = self._tick_count
        self.weighted_memories.append(mem)

        # Keep old memory list too (backward compat)
        self.memory.append(content)
        if len(self.memory) > 20:
            self.memory = self.memory[-20:]

        # Prune old low-importance memories
        if len(self.weighted_memories) > 30:
            self.weighted_memories.sort(key=lambda m: m.importance, reverse=True)
            self.weighted_memories = self.weighted_memories[:20]

        return mem

    def _top_memories(self, n=5):
        """Return top N memories by importance, aging high-age ones."""
        for m in self.weighted_memories:
            m.age()
        sorted_mems = sorted(
            self.weighted_memories,
            key=lambda m: (m.unresolved * 3 + m.importance) / (1 + m.tick_age * 0.05),
            reverse=True,
        )
        return sorted_mems[:n]

    def _unresolved_memories(self):
        """Return all unresolved memories (open loops)."""
        return [m for m in self.weighted_memories if m.unresolved]

    # ═══════════════════════════════════════════════════════════════
    # Relationship System
    # ═══════════════════════════════════════════════════════════════

    def _ensure_relationship(self, target_id, target_name):
        """Get or create a Relationship2D with another agent."""
        if target_id not in self.relationships:
            self.relationships[target_id] = Relationship2D(target_id, target_name)
        return self.relationships[target_id]

    def _modify_relationship_from_speech(self, target_id, target_name,
                                          my_emotion_dom, text):
        """Adjust relationship dimensions based on conversation content and emotion."""
        rel = self._ensure_relationship(target_id, target_name)

        # Base: positive social interaction boosts trust & affection slightly
        rel.modify('trust', 0.3, memory=f"我和{target_name}聊了天")
        rel.modify('affection', 0.2)

        # Emotion-driven modifiers
        if my_emotion_dom == 'happiness':
            rel.modify('affection', 0.5)
        elif my_emotion_dom == 'sadness':
            rel.modify('trust', 0.8, memory=f"向{target_name}倾诉了心事")
        elif my_emotion_dom == 'anger':
            rel.modify('resentment', 0.3)
        elif my_emotion_dom == 'loneliness':
            rel.modify('affection', 0.6)

        # Check for stage transitions
        self._check_stage_transition(target_id)

    def _check_stage_transition(self, target_id):
        """Check if relationship stage changed and record event."""
        # Stage is computed fresh each time from dimensions
        pass  # Stage transitions are detected in world.py via to_dict() diff

    # ═══════════════════════════════════════════════════════════════
    # Belief System
    # ═══════════════════════════════════════════════════════════════

    def _ensure_belief(self, target_id):
        """Get or create a Belief about another agent."""
        if target_id not in self.beliefs:
            self.beliefs[target_id] = Belief(target_id)
        return self.beliefs[target_id]

    def _update_belief_from_interaction(self, target_id, action, text):
        """Update belief about target based on direct interaction."""
        belief = self._ensure_belief(target_id)

        if action == "speak":
            # Direct conversation gives honest signal
            belief.update('honesty', 6, 0.7, source="direct")
            belief.update('kindness', 6, 0.5, source="direct")
            # Check text for competence/reliability signals
            if any(w in text for w in ['知道', '懂', '会', '做', '修', '帮']):
                belief.update('competence', 6, 0.5, source="direct")

        elif action == "interact":
            belief.update('competence', 5.5, 0.4, source="observation")

    def _check_belief_contradictions(self):
        """Return list of belief contradictions that need resolving."""
        all_contradictions = []
        for target_id, belief in self.beliefs.items():
            for dim in BELIEF_DIMENSIONS:
                val = getattr(belief, dim)
                conf = belief.confidence.get(dim, 0.3)
                if conf > 0.5 and (val <= 3 or val >= 8):
                    # Strong belief — no contradiction (it's confirmed)
                    pass
                elif conf < 0.3 and val != 5:
                    # Uncertain belief — mark as needing resolution
                    all_contradictions.append({
                        "target_id": target_id,
                        "dimension": dim,
                        "label": BELIEF_LABELS.get(dim, dim),
                        "value": val,
                        "confidence": conf,
                    })
        return all_contradictions[:3]

    # ═══════════════════════════════════════════════════════════════
    # Goal & Plan System
    # ═══════════════════════════════════════════════════════════════

    def _pick_new_goal(self, world):
        """Pick a new long-term goal based on needs, mood, open loops, time of day."""
        lowest_need = self.needs.lowest()
        p = self.personality
        phase = world.day_phase()
        is_night = world.is_sleeping_hours()

        # ── Nighttime: go home to sleep ──
        if is_night:
            return Goal('rest',
                        f'夜深了，回家睡觉',
                        max_progress=60, priority=10)

        # ── Dawn: wake up, start the day ──
        if phase == 'dawn' and self.rng.random() < 0.5:
            morning_goals = [
                Goal('explore', '天亮了，出去走走呼吸新鲜空气', priority=6),
                Goal('socialize', '早起去看看大家都在做什么', priority=5),
                Goal('work', '新的一天，开始干活', priority=5),
            ]
            return self.rng.choice(morning_goals)

        # ── Dusk: wrap up, head toward home area ──
        if phase == 'dusk' and self.rng.random() < 0.4:
            return Goal('rest', '天快黑了，准备回家', max_progress=40, priority=7)

        candidates = []

        # Need-driven goals
        if self.needs.social < 30:
            candidates.append(Goal('socialize', '找人聊聊天，缓解孤独感',
                                   priority=8 if self.mood.loneliness > 6 else 5))
        if self.needs.rest < 25:
            candidates.append(Goal('rest', '找个安静的地方休息一下', priority=6))
        if self.needs.hunger < 25:
            candidates.append(Goal('explore', '去集市或水井找点吃的', priority=5))
        if self.needs.purpose < 30:
            candidates.append(Goal('work', '做点有意义的事让今天充实起来', priority=6))

        # Open-loop driven goals
        unresolved = self._unresolved_memories()
        for mem in unresolved:
            if mem.importance >= 7:
                for aid in mem.related_agents:
                    candidates.append(Goal(
                        'gossip_investigate',
                        f'搞清楚: {mem.content[:30]}',
                        target_agent_id=aid,
                        priority=9,
                    ))

        # Relationship-driven goals
        for rid, rel in self.relationships.items():
            stage = rel.stage()
            if stage == RelationshipStage.ROMANTIC_INTEREST and p['E'] >= 0.5:
                candidates.append(Goal(
                    'romance',
                    f'想和{rel.target_name}的关系更进一步',
                    target_agent_id=rid,
                    priority=9,
                ))
            if stage == RelationshipStage.ENEMY and rel.resentment >= 7:
                candidates.append(Goal(
                    'resolve_conflict',
                    f'和{rel.target_name}的恩怨需要解决',
                    target_agent_id=rid,
                    priority=7,
                ))

        # Personality-driven
        if p['O'] > 0.7 and self.rng.random() < 0.3:
            candidates.append(Goal('explore', '在小镇四处走走，看看新鲜事', priority=4))
        if p['N'] > 0.6 and self.mood.anxiety > 6:
            candidates.append(Goal('rest', '心里很不安，需要冷静下来', priority=8))

        # Default fallback
        if not candidates:
            candidates.append(Goal('socialize', '在小镇上找人说说话', priority=3))
            candidates.append(Goal('explore', '四处走走', priority=3))

        candidates.sort(key=lambda g: g.priority, reverse=True)
        # Weighted random pick from top candidates
        top = candidates[:3]
        chosen = self.rng.choices(
            top,
            weights=[g.priority for g in top],
            k=1,
        )[0]
        chosen.tick_created = self._tick_count
        return chosen

    def _derive_plan_from_goal(self, goal, world):
        """Create a ShortTermPlan from a Goal."""
        steps = []

        if goal.type == 'socialize':
            if goal.target_agent_id and goal.target_agent_id in world.agents:
                target = world.agents[goal.target_agent_id]
                steps = [
                    {"action_type": "move", "target": target.name,
                     "location": (target.x, target.y), "completed": False},
                    {"action_type": "speak", "target": target.name,
                     "location": None, "completed": False},
                ]
            else:
                # Find someone to talk to
                steps = [
                    {"action_type": "move", "target": "篝火",
                     "location": None, "completed": False},
                    {"action_type": "speak", "target": "附近的人",
                     "location": None, "completed": False},
                ]

        elif goal.type == 'romance':
            if goal.target_agent_id and goal.target_agent_id in world.agents:
                target = world.agents[goal.target_agent_id]
                steps = [
                    {"action_type": "move", "target": target.name,
                     "location": (target.x, target.y), "completed": False},
                    {"action_type": "speak", "target": target.name,
                     "location": None, "completed": False},
                    {"action_type": "speak", "target": target.name,
                     "location": None, "completed": False},
                ]

        elif goal.type == 'resolve_conflict':
            if goal.target_agent_id and goal.target_agent_id in world.agents:
                target = world.agents[goal.target_agent_id]
                steps = [
                    {"action_type": "move", "target": target.name,
                     "location": (target.x, target.y), "completed": False},
                    {"action_type": "speak", "target": target.name,
                     "location": None, "completed": False},
                ]

        elif goal.type == 'rest':
            # At night or dusk: go to own home
            if '回家' in goal.description or '夜' in goal.description:
                steps = [
                    {"action_type": "move", "target": "家",
                     "location": (self.home_x, self.home_y), "completed": False},
                    {"action_type": "interact", "target": "家",
                     "location": None, "completed": False},
                    {"action_type": "idle", "target": "",
                     "location": None, "completed": False},
                ]
            else:
                rest_spots = ['长椅', '篝火', '小梅的家', '老王的屋子', '阿诗的住处']
                chosen = self.rng.choice(rest_spots)
                steps = [
                    {"action_type": "move", "target": chosen,
                     "location": None, "completed": False},
                    {"action_type": "interact", "target": chosen,
                     "location": None, "completed": False},
                ]

        elif goal.type == 'explore':
            spots = ['集市', '篝火', '水井', '大树']
            chosen = self.rng.choice(spots)
            steps = [
                {"action_type": "move", "target": chosen,
                 "location": None, "completed": False},
                {"action_type": "interact", "target": chosen,
                 "location": None, "completed": False},
            ]

        elif goal.type in ('gossip_spread', 'gossip_investigate'):
            if goal.target_agent_id and goal.target_agent_id in world.agents:
                target = world.agents[goal.target_agent_id]
                steps = [
                    {"action_type": "move", "target": target.name,
                     "location": (target.x, target.y), "completed": False},
                    {"action_type": "speak", "target": target.name,
                     "location": None, "completed": False},
                ]
            else:
                steps = [
                    {"action_type": "move", "target": "集市",
                     "location": None, "completed": False},
                    {"action_type": "speak", "target": "附近的人",
                     "location": None, "completed": False},
                ]

        else:
            steps = [
                {"action_type": "move", "target": "篝火",
                 "location": None, "completed": False},
                {"action_type": "interact", "target": "篝火",
                 "location": None, "completed": False},
            ]

        return ShortTermPlan(steps, goal_desc=goal.description)

    def _maybe_change_goal(self, world):
        """Check if current goal needs replacement."""
        if self.current_goal is None:
            self.current_goal = self._pick_new_goal(world)
            self.current_plan = self._derive_plan_from_goal(self.current_goal, world)
            return

        # Goal complete
        if self.current_goal.is_complete():
            self._add_memory(
                f"完成了目标: {self.current_goal.description}",
                importance=4,
            )
            self.current_goal = self._pick_new_goal(world)
            self.current_plan = self._derive_plan_from_goal(self.current_goal, world)
            return

        # Goal too old (>30 ticks)
        if self._tick_count - self.current_goal.tick_created > 30:
            self.current_goal = self._pick_new_goal(world)
            self.current_plan = self._derive_plan_from_goal(self.current_goal, world)
            return

        # Plan exhausted
        if self.current_plan and self.current_plan.is_complete():
            self.current_goal.advance(25)
            if self.current_goal.is_complete():
                self.current_goal = self._pick_new_goal(world)
            self.current_plan = self._derive_plan_from_goal(self.current_goal, world)

    # ═══════════════════════════════════════════════════════════════
    # Perception
    # ═══════════════════════════════════════════════════════════════

    def perceive(self, world):
        return {
            "nearby_agents": world.get_nearby_agents(self.id, self.x, self.y, radius=6),
            "nearby_objects": world.get_nearby_objects(self.x, self.y, radius=5),
            "recent_speech": world.get_recent_speech_for(self.id),
        }

    # ═══════════════════════════════════════════════════════════════
    # Main Tick
    # ═══════════════════════════════════════════════════════════════

    async def tick(self, world, llm_client):
        """One full cycle: decay → mood → goal/plan → perceive → decide → execute."""
        self._tick_count += 1

        # 1. Decay
        self.needs.decay()
        self.mood.decay()
        self.mood.lingering_apply()

        # 2. Auto-mood from needs
        if self.needs.social < 20:
            self.mood.feel('loneliness', 1.5, linger=2)
        if self.needs.rest < 15:
            self.mood.feel('anxiety', 1.0, linger=1)

        # 3. Check belief contradictions (can create open loops)
        contradictions = self._check_belief_contradictions()
        for c in contradictions:
            self._add_memory(
                f"我对{c['target_id']}的{c['label']}不太确定",
                importance=5,
                emotion='anxious',
                related_agents=[c['target_id']],
                unresolved=True,
            )

        # 4. Maintain goal/plan
        self._maybe_change_goal(world)

        # 5. Perceive
        perception = self.perceive(world)

        # 5a. Update beliefs from observation
        for a in perception.get("nearby_agents", []):
            self._ensure_belief(a["id"])
            # Observing someone near others = social signal
            belief = self.beliefs[a["id"]]
            if belief.confidence.get('kindness', 0.3) < 0.5:
                belief.update('kindness', 5, 0.3, source="observation")

        # 6. Build state for LLM
        state = self._build_state(perception)

        # 7. LLM decides
        action = await llm_client.decide(state, perception)

        # 8. Execute action
        return await self._execute(action, world, perception)

    # ═══════════════════════════════════════════════════════════════
    # State Builder (for LLM prompt)
    # ═══════════════════════════════════════════════════════════════

    def _build_state(self, perception):
        """Build comprehensive state dict with all 8 layers for LLM prompt."""
        return {
            "name": self.name,
            "role": self.role,
            "x": self.x, "y": self.y,
            "personality": self.personality,
            "backstory": self.backstory,

            # Layer 3: Goal & Plan
            "goal": self.current_goal.to_dict() if self.current_goal else None,
            "plan": self.current_plan.to_dict() if self.current_plan else None,

            # Layer 7: Mood Vector
            "mood_vector": self.mood.to_dict(),
            "dominant_mood": self.mood.dominate(),
            "mood_label": self.mood.mood_label(),

            # Needs
            "needs": self.needs.to_dict(),
            "needs_lowest": self.needs.lowest(),

            # Layer 1: Multi-dimensional relationships
            "relationships": [
                r.to_dict() for r in self.relationships.values()
            ],

            # Layer 8: Beliefs
            "beliefs": {
                rid: b.to_dict() for rid, b in self.beliefs.items()
            },

            # Layer 2: Weighted memories (top 5)
            "top_memories": [m.summary() for m in self._top_memories(5)],
            "unresolved_memories": [m.summary() for m in self._unresolved_memories()],

            # Gossip heard
            "gossip_heard": self.gossip_heard[-5:],

            # Legacy compat
            "current_goal": self.current_goal.description if self.current_goal else "探索小镇",
            "emotion": self.mood.mood_label(),
            "memory": self.memory,
        }

    # ═══════════════════════════════════════════════════════════════
    # Execute
    # ═══════════════════════════════════════════════════════════════

    async def _execute(self, action, world, perception):
        action_type = action.get("action", "idle")
        target = action.get("target", "")
        text = action.get("text", "")
        thought = action.get("thought", "")
        gossip_about = action.get("gossip_about", "")

        # Night silence: during sleeping hours, only move home or idle
        if world.is_sleeping_hours() and action_type in ("speak", "interact"):
            return self._exec_idle({"thought": "夜深了，大家都在睡觉..."})

        if action_type == "move":
            return self._exec_move(action, world, perception)

        elif action_type == "speak" and text:
            return self._exec_speak(action, world, perception)

        elif action_type == "interact":
            return self._exec_interact(action, world)

        else:
            return self._exec_idle(action)

    def _exec_move(self, action, world, perception):
        target = action.get("target", "")
        thought = action.get("thought", "")

        # Check if we're trying to approach a specific agent
        approaching_agent_id = None
        for aid, a in world.agents.items():
            if aid != self.id and a.name == target:
                approaching_agent_id = aid
                break

        target_pos = self._resolve_target(target, world, perception)
        if target_pos:
            self.path = world.bfs_path((self.x, self.y), target_pos, max_steps=20)
            steps = min(len(self.path), 3 + int(self.personality.get("E", 0.5) * 2))
            if steps > 0 and self.path:
                for _ in range(steps):
                    if self.path:
                        nx, ny = self.path.pop(0)
                        if world.is_walkable(nx, ny):
                            # Enforce min distance: skip tile if too close to non-target agent
                            if approaching_agent_id:
                                too_close = world.is_too_close_to_agents(
                                    nx, ny, exclude_id=self.id, min_dist=2)
                            else:
                                too_close = world.is_too_close_to_agents(
                                    nx, ny, exclude_id=self.id, min_dist=4)
                            if too_close and not (approaching_agent_id and
                                    abs(nx - world.agents[approaching_agent_id].x) +
                                    abs(ny - world.agents[approaching_agent_id].y) <= 2):
                                continue
                            self.x, self.y = nx, ny
                self._idle_ticks = 0

        # After moving, push away from other agents if too close
        # Always push away from others — even when approaching a target, keep some distance
        self.x, self.y = world.push_away_from_agents(
            self.x, self.y, exclude_id=self.id,
            min_dist=4 if not approaching_agent_id else 2)

        # Clamp to visible area — MUST be last (sprite is 128px tall, canvas is 31 tiles)
        self.x = max(0, min(39, self.x))
        self.y = max(5, min(28, self.y))

        self._idle_ticks += 1
        if self.current_goal and not self.current_goal.is_complete():
            self.current_goal.advance(5)

        if self.current_plan and not self.current_plan.is_complete():
            self.current_plan.advance()

        return self._make_event("agent_update", thought=thought, importance=0)

    def _exec_speak(self, action, world, perception):
        target = action.get("target", "")
        text = action.get("text", "")
        thought = action.get("thought", "")
        gossip_about = action.get("gossip_about", "")

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
            self._modify_relationship_from_speech(
                target_id, target, self.mood.dominate(), text,
            )
            self._update_belief_from_interaction(target_id, "speak", text)
            world.record_speech_to(target_id, self.id, self.name, text)

        # Handle gossip
        gossip_event = None
        if gossip_about and target_id:
            gossip_event = world.spread_gossip(self.id, target_id, gossip_about, text)

        # Record memory
        self._add_memory(
            f"我对{target}说: {text}",
            importance=6,
            emotion=self.mood.dominate(),
            related_agents=[target_id] if target_id else [],
        )

        # Feel good after socializing
        self.mood.feel('happiness', 1.5, linger=2)
        self.mood.feel('loneliness', -1.0)
        if self.mood.sadness > 4:
            self.mood.feel('sadness', -0.5)

        if self.current_goal and not self.current_goal.is_complete():
            self.current_goal.advance(15)

        if self.current_plan and not self.current_plan.is_complete():
            self.current_plan.advance()

        imp = 4 if gossip_about else 2
        result = self._make_event("speech", thought=thought, importance=imp)
        result["agent_name"] = self.name
        result["text"] = text
        result["target"] = target
        result["gossip_about"] = gossip_about
        result["gossip_event"] = gossip_event
        return result

    def _exec_interact(self, action, world):
        target = action.get("target", "")
        thought = action.get("thought", "")
        obj_name = target or "周围的东西"

        if "篝火" in obj_name or "火" in obj_name:
            self.needs.replenish('social', 10)
            self.needs.replenish('purpose', 8)
            self.mood.feel('happiness', 0.5, linger=1)
        elif "水井" in obj_name or "井" in obj_name:
            self.needs.replenish('hunger', 15)
            self.mood.feel('happiness', 0.3)
        elif "长椅" in obj_name or "椅" in obj_name:
            self.needs.replenish('rest', 30)
            self.mood.feel('happiness', 1.0, linger=2)
        elif "集市" in obj_name:
            self.needs.replenish('hunger', 20)
            self.needs.replenish('purpose', 10)
            self.mood.feel('happiness', 1.0, linger=1)
        elif "家" in obj_name:
            self.needs.replenish('rest', 40)
            self.needs.replenish('purpose', 5)
            self.mood.feel('happiness', 1.5, linger=2)
        elif "树" in obj_name:
            self.needs.replenish('rest', 10)
            self.mood.feel('happiness', 0.5)
        else:
            self.needs.replenish('purpose', 5)

        self._idle_ticks = 0
        self._add_memory(f"我在{obj_name}这里互动了一下", importance=3)

        if self.current_goal and not self.current_goal.is_complete():
            self.current_goal.advance(20)

        if self.current_plan and not self.current_plan.is_complete():
            self.current_plan.advance()

        result = self._make_event("interaction", thought=thought, importance=1)
        result["agent_name"] = self.name
        result["target"] = obj_name
        return result

    def _exec_idle(self, action):
        thought = action.get("thought", "")
        self._idle_ticks += 1
        self.needs.replenish('rest', 8)
        self.mood.feel('happiness', 0.3)

        return self._make_event("agent_idle", thought=thought, importance=0)

    def _make_event(self, event_type, thought="", importance=0):
        return {
            "type": event_type,
            "agent_id": self.id,
            "x": self.x, "y": self.y,
            "path": self.path,
            "thought": thought,
            "emotion": self.mood.mood_label(),
            "emoji": self.mood.legacy_emotion()["emoji"],
            "needs": self.needs.summary(),
            "importance": importance,
        }

    # ═══════════════════════════════════════════════════════════════
    # Gossip Reception
    # ═══════════════════════════════════════════════════════════════

    def hear_gossip(self, about_id, about_name, valence, text, source_id=None):
        """Receive gossip — use credibility system to adjust impact."""
        self.gossip_heard.append(f"{about_name}: {text}")
        if len(self.gossip_heard) > 10:
            self.gossip_heard = self.gossip_heard[-10:]

        # Compute credibility
        credibility = 0.3  # default

        if source_id and source_id in self.relationships:
            rel = self.relationships[source_id]
            source_trust = rel.trust / 10.0  # 0-1
        else:
            source_trust = 0.3

        if about_id and about_id in self.beliefs:
            belief = self.beliefs[about_id]
            # How plausible is this claim given what I believe?
            claim_plausibility = 0.5
            if valence < 0 and belief.kindness > 7:
                claim_plausibility = 0.3  # "They're kind, hard to believe bad things"
            elif valence > 0 and belief.kindness < 3:
                claim_plausibility = 0.3  # "They're not kind, hard to believe good things"
            else:
                claim_plausibility = 0.6
        else:
            claim_plausibility = 0.5

        if about_id and about_id in self.relationships:
            rel_strength = sum(
                getattr(self.relationships[about_id], d, 5)
                for d in ['trust', 'affection', 'respect']
            ) / 30.0
        else:
            rel_strength = 0.3

        credibility = source_trust * claim_plausibility * (0.3 + rel_strength * 0.7)
        effect = valence * credibility

        # Gossip about me
        if about_id == self.id:
            if valence < 0:
                self.mood.feel('sadness', abs(effect) * 1.5, linger=3)
                self.mood.feel('anger', abs(effect), linger=1)
                self._add_memory(
                    f"听说有人在说我坏话: {text[:30]}",
                    importance=7,
                    emotion='hurt',
                    related_agents=[source_id] if source_id else [],
                    unresolved=True,
                )
            else:
                self.mood.feel('happiness', effect, linger=2)

        # Update belief
        if about_id and about_id not in self.beliefs:
            self._ensure_belief(about_id)
        if about_id in self.beliefs:
            dim = 'kindness' if valence > 0 else 'honesty'
            val = min(10, max(0, 5 + valence * 2))
            self.beliefs[about_id].update(dim, val, credibility, source="gossip")

        # Update relationship
        rel = self._ensure_relationship(about_id, about_name)
        if effect > 0:
            rel.modify('trust', effect * 0.5, memory=f"听说: {text[:20]}")
            rel.modify('affection', effect * 0.3)
        else:
            rel.modify('resentment', abs(effect) * 0.3)
            rel.modify('trust', effect * 0.3)

        # Low credibility can create doubt about the source
        if credibility < 0.2 and source_id and source_id in self.relationships:
            self.relationships[source_id].modify('trust', -0.2)
            self._add_memory(
                f"不太相信{source_id}说的话，可信度太低了",
                importance=4,
                emotion='doubt',
                related_agents=[source_id],
            )

    # ═══════════════════════════════════════════════════════════════
    # Helpers
    # ═══════════════════════════════════════════════════════════════

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

    # ═══════════════════════════════════════════════════════════════
    # Serialization (backward-compatible)
    # ═══════════════════════════════════════════════════════════════

    def to_dict(self):
        legacy_emo = self.mood.legacy_emotion()
        return {
            # Legacy keys (frontend depends on these)
            "id": self.id,
            "name": self.name,
            "role": self.role,
            "x": self.x, "y": self.y,
            "color": self.color,
            "personality": self.personality,
            "backstory": self.backstory,
            "current_goal": self.current_goal.description if self.current_goal else "探索小镇",
            "memory": self.memory,
            "emotion": {
                "type": legacy_emo["type"],
                "intensity": legacy_emo["intensity"],
                "emoji": legacy_emo["emoji"],
            },
            "needs": self.needs.to_dict(),
            "relationships": {
                rid: r.to_dict() for rid, r in self.relationships.items()
            },
            "gossip_heard": self.gossip_heard[-5:],

            # New keys (frontend can gradually adopt)
            "mood_vector": self.mood.to_dict(),
            "beliefs": {
                rid: b.to_dict() for rid, b in self.beliefs.items()
            },
            "open_loops": [m.summary() for m in self._unresolved_memories()],
            "goal_progress": self.current_goal.to_dict() if self.current_goal else None,
            "plan_summary": self.current_plan.to_dict() if self.current_plan else None,
            "relationship_stages": {
                rid: {
                    "stage": r.stage().value,
                    "label": r.stage().label(),
                    "emoji": r.stage().emoji(),
                }
                for rid, r in self.relationships.items()
            },
        }
