"""Data models for the motivation simulation — 8-layer agent architecture."""

import time
from enum import Enum


# ═══════════════════════════════════════════════════════════════════════
# Relationship Stage
# ═══════════════════════════════════════════════════════════════════════

class RelationshipStage(Enum):
    STRANGER = "stranger"
    ACQUAINTANCE = "acquaintance"
    FRIEND = "friend"
    CLOSE_FRIEND = "close_friend"
    ROMANTIC_INTEREST = "romantic_interest"
    LOVER = "lover"
    ENEMY = "enemy"
    RIVAL = "rival"

    def label(self):
        return {
            "stranger": "陌生人", "acquaintance": "认识",
            "friend": "朋友", "close_friend": "密友",
            "romantic_interest": "暗恋/好感", "lover": "恋人",
            "enemy": "敌人", "rival": "对手",
        }.get(self.value, self.value)

    def emoji(self):
        return {
            "stranger": "😶", "acquaintance": "👋", "friend": "🙂",
            "close_friend": "🤝", "romantic_interest": "💕",
            "lover": "❤️", "enemy": "😡", "rival": "😤",
        }.get(self.value, "😶")


STAGE_THRESHOLDS = {
    RelationshipStage.CLOSE_FRIEND: {"trust": 6, "affection": 6, "respect": 5},
    RelationshipStage.FRIEND: {"trust": 4, "affection": 4, "respect": 3},
    RelationshipStage.ROMANTIC_INTEREST: {"attraction": 5, "trust": 3, "affection": 4},
    RelationshipStage.LOVER: {"attraction": 7, "trust": 6, "affection": 7},
    RelationshipStage.RIVAL: {"jealousy": 5, "respect": 3},
}

ENEMY_CONDITIONS = [
    {"resentment": 5},
    {"trust": 2, "affection": 1, "operator": "and_max"},
]


# ═══════════════════════════════════════════════════════════════════════
# Weighted Memory
# ═══════════════════════════════════════════════════════════════════════

class WeightedMemory:
    __slots__ = ('content', 'importance', 'emotion', 'related_agents',
                 'tick_age', 'unresolved', 'tick_created')

    def __init__(self, content, importance=5, emotion="calm",
                 related_agents=None, unresolved=False):
        self.content = content
        self.importance = min(10, max(0, importance))
        self.emotion = emotion
        self.related_agents = related_agents or []
        self.tick_age = 0
        self.unresolved = unresolved
        self.tick_created = 0

    def age(self):
        self.tick_age += 1
        if self.tick_age > 20 and self.unresolved:
            self.importance = max(0, self.importance - 0.3)

    def resolve(self):
        self.unresolved = False

    def summary(self):
        prefix = "⚡" if self.unresolved else "·"
        return f"{prefix}[{self.importance}] {self.content[:60]}"


# ═══════════════════════════════════════════════════════════════════════
# Mood Vector (5-dimensional continuous emotion space)
# ═══════════════════════════════════════════════════════════════════════

MOOD_DIMENSIONS = ['happiness', 'sadness', 'anxiety', 'anger', 'loneliness']
EMOJI_MAP = {
    'happiness': '😊', 'sadness': '😢', 'anxiety': '😰',
    'anger': '😠', 'loneliness': '🥺',
}
LABEL_MAP = {
    'happiness': '愉悦', 'sadness': '悲伤', 'anxiety': '焦虑',
    'anger': '愤怒', 'loneliness': '孤独',
}


class MoodVector:
    __slots__ = ('happiness', 'sadness', 'anxiety', 'anger', 'loneliness',
                 '_linger')  # _linger: {dim: remaining_ticks}

    def __init__(self):
        self.happiness = 5.0
        self.sadness = 1.0
        self.anxiety = 2.0
        self.anger = 0.5
        self.loneliness = 3.0
        self._linger = {}  # dim -> ticks remaining

    def feel(self, dimension, delta, linger=0):
        """Apply an emotional delta with optional lingering duration."""
        if dimension not in MOOD_DIMENSIONS:
            return
        current = getattr(self, dimension)
        setattr(self, dimension, min(10.0, max(0.0, current + delta)))
        if linger > 0:
            self._linger[dimension] = max(self._linger.get(dimension, 0), linger)

    def decay(self, dt=1.0):
        """Gradually decay all dimensions toward baseline."""
        baselines = {'happiness': 5.0, 'sadness': 1.0, 'anxiety': 2.0,
                     'anger': 0.5, 'loneliness': 3.0}
        for dim in MOOD_DIMENSIONS:
            current = getattr(self, dim)
            baseline = baselines[dim]
            rate = 0.15 * dt
            setattr(self, dim, current + (baseline - current) * rate)

    def lingering_apply(self):
        """Apply lingering effects — strong emotions that resist decay."""
        done = []
        for dim, ticks in self._linger.items():
            if ticks <= 0:
                done.append(dim)
                continue
            current = getattr(self, dim)
            if current > 4:
                setattr(self, dim, min(10, current))
            self._linger[dim] = ticks - 1
        for d in done:
            del self._linger[d]

    def dominate(self):
        """Return the dimension with the highest value above baseline."""
        baselines = {'happiness': 5.0, 'sadness': 1.0, 'anxiety': 2.0,
                     'anger': 0.5, 'loneliness': 3.0}
        max_delta = 0
        dominant = 'happiness'
        for dim in MOOD_DIMENSIONS:
            delta = getattr(self, dim) - baselines[dim]
            if delta > max_delta:
                max_delta = delta
                dominant = dim
        return dominant

    def mood_label(self):
        baselines = {'happiness': 5.0, 'sadness': 1.0, 'anxiety': 2.0,
                     'anger': 0.5, 'loneliness': 3.0}
        dom = self.dominate()
        val = getattr(self, dom)
        if val < baselines.get(dom, 5) + 1:
            return "平静"
        return f"{EMOJI_MAP.get(dom, '')}{LABEL_MAP.get(dom, dom)}({val:.0f})"

    def summary(self):
        parts = []
        for dim in MOOD_DIMENSIONS:
            v = getattr(self, dim)
            if v >= 3:
                parts.append(f"{LABEL_MAP[dim]}{v:.0f}")
        return " ".join(parts) if parts else "平静"

    def to_dict(self):
        return {
            "happiness": round(self.happiness, 1),
            "sadness": round(self.sadness, 1),
            "anxiety": round(self.anxiety, 1),
            "anger": round(self.anger, 1),
            "loneliness": round(self.loneliness, 1),
            "dominant": self.dominate(),
            "label": self.mood_label(),
            "lingering": list(self._linger.keys()),
        }

    def legacy_emotion(self):
        """Backward-compat: return {type, intensity, emoji} like old Emotion."""
        dom = self.dominate()
        val = getattr(self, dom)
        baselines = {'happiness': 5.0, 'sadness': 1.0, 'anxiety': 2.0,
                     'anger': 0.5, 'loneliness': 3.0}
        threshold = baselines.get(dom, 5) + 1
        if val < threshold or dom == 'happiness' and val < 5:
            return {"type": "calm", "intensity": 2.0, "emoji": "😌"}
        return {"type": dom, "intensity": val, "emoji": EMOJI_MAP.get(dom, "😶")}


# ═══════════════════════════════════════════════════════════════════════
# Relationship 2D (6-dimensional relationship vector)
# ═══════════════════════════════════════════════════════════════════════

REL_DIMENSIONS = ['trust', 'affection', 'respect', 'attraction', 'jealousy', 'resentment']
REL_LABELS = {
    'trust': '信任', 'affection': '好感', 'respect': '尊敬',
    'attraction': '吸引', 'jealousy': '嫉妒', 'resentment': '怨恨',
}


class Relationship2D:
    __slots__ = ('target_id', 'target_name', 'trust', 'affection',
                 'respect', 'attraction', 'jealousy', 'resentment',
                 'shared_memories', 'last_interaction')

    def __init__(self, target_id, target_name,
                 trust=5, affection=5, respect=5,
                 attraction=0, jealousy=0, resentment=0):
        self.target_id = target_id
        self.target_name = target_name
        self.trust = trust
        self.affection = affection
        self.respect = respect
        self.attraction = attraction
        self.jealousy = jealousy
        self.resentment = resentment
        self.shared_memories = []
        self.last_interaction = 0

    def modify(self, dimension, delta, memory=None):
        """Modify one dimension of the relationship."""
        if dimension not in REL_DIMENSIONS:
            return
        current = getattr(self, dimension)
        setattr(self, dimension, max(0, min(10, current + delta)))
        if memory:
            self.shared_memories.append(memory)
            if len(self.shared_memories) > 12:
                self.shared_memories = self.shared_memories[-12:]
        self.last_interaction = time.time()

    def stage(self):
        """Determine relationship stage from 6D vector."""
        # Check enemy conditions first (OR logic)
        if self.resentment >= 5:
            return RelationshipStage.ENEMY
        if self.trust <= 2 and self.affection <= 1:
            return RelationshipStage.ENEMY

        # Check special stages (checked in priority order)
        if self.attraction >= 7 and self.trust >= 6 and self.affection >= 7:
            return RelationshipStage.LOVER
        if self.attraction >= 5 and self.trust >= 3 and self.affection >= 4:
            return RelationshipStage.ROMANTIC_INTEREST
        if self.jealousy >= 5 and self.respect >= 3:
            return RelationshipStage.RIVAL

        # Friendship ladder
        if self.trust >= 6 and self.affection >= 6 and self.respect >= 5:
            return RelationshipStage.CLOSE_FRIEND
        if self.trust >= 4 and self.affection >= 4 and self.respect >= 3:
            return RelationshipStage.FRIEND
        if self.trust >= 2 or self.affection >= 2 or self.respect >= 2:
            return RelationshipStage.ACQUAINTANCE

        return RelationshipStage.STRANGER

    def legacy_affinity(self):
        """Backward-compat: approximate old -10..+10 affinity from 6D."""
        positive = (self.trust + self.affection + self.respect + self.attraction) / 4
        negative = (self.jealousy + self.resentment) / 2
        return round((positive - negative) * 2 - 10, 1)

    def summary(self):
        st = self.stage()
        dims = []
        for d in REL_DIMENSIONS:
            v = getattr(self, d)
            if v >= 6:
                dims.append(f"{REL_LABELS[d]}{v:.0f}")
        dim_str = " ".join(dims) if dims else "平淡"
        return f"{st.emoji()}{self.target_name} [{st.label()}] {dim_str}"

    def to_dict(self):
        return {
            "name": self.target_name,
            "affinity": self.legacy_affinity(),
            "stage": self.stage().value,
            "stage_label": self.stage().label(),
            "stage_emoji": self.stage().emoji(),
            "dimensions": {
                "trust": self.trust,
                "affection": self.affection,
                "respect": self.respect,
                "attraction": self.attraction,
                "jealousy": self.jealousy,
                "resentment": self.resentment,
            },
            "tags": self._tags_from_dims(),
            "memories": self.shared_memories[-3:],
        }

    def _tags_from_dims(self):
        tags = []
        if self.attraction >= 6:
            tags.append("心动")
        elif self.attraction >= 4:
            tags.append("在意")
        if self.resentment >= 5:
            tags.append("积怨")
        if self.jealousy >= 5:
            tags.append("嫉妒")
        if self.trust >= 7:
            tags.append("信任")
        elif self.trust <= 3:
            tags.append("怀疑")
        if self.affection >= 7:
            tags.append("喜欢")
        if self.respect >= 7:
            tags.append("尊敬")
        return tags


# ═══════════════════════════════════════════════════════════════════════
# Goal & Short-Term Plan
# ═══════════════════════════════════════════════════════════════════════

GOAL_TYPES = [
    'socialize', 'resolve_conflict', 'explore', 'rest', 'work',
    'romance', 'gossip_spread', 'gossip_investigate', 'help_other',
]

GOAL_LABELS = {
    'socialize': '社交', 'resolve_conflict': '解决矛盾', 'explore': '探索',
    'rest': '休息', 'work': '工作', 'romance': '感情',
    'gossip_spread': '传播消息', 'gossip_investigate': '打听消息',
    'help_other': '帮助他人',
}


class Goal:
    __slots__ = ('type', 'description', 'progress', 'max_progress',
                 'tick_created', 'target_agent_id', 'priority')

    def __init__(self, goal_type, description, target_agent_id=None,
                 max_progress=100, priority=5):
        self.type = goal_type
        self.description = description
        self.progress = 0
        self.max_progress = max_progress
        self.tick_created = 0
        self.target_agent_id = target_agent_id
        self.priority = priority

    def advance(self, amount=10):
        self.progress = min(self.max_progress, self.progress + amount)

    def is_complete(self):
        return self.progress >= self.max_progress

    def summary(self):
        pct = self.progress / max(self.max_progress, 1) * 100
        target = f" → {self.target_agent_id}" if self.target_agent_id else ""
        return f"[{GOAL_LABELS.get(self.type, self.type)}] {self.description}{target} ({pct:.0f}%)"

    def to_dict(self):
        return {
            "type": self.type,
            "label": GOAL_LABELS.get(self.type, self.type),
            "description": self.description,
            "progress": round(self.progress, 1),
            "max_progress": round(self.max_progress, 1),
            "target_agent_id": self.target_agent_id,
            "priority": self.priority,
        }


class ShortTermPlan:
    __slots__ = ('steps', 'current_step', 'tick_remaining', 'goal_desc')

    def __init__(self, steps, goal_desc=""):
        self.steps = steps  # [{action_type, target, location, completed}]
        self.current_step = 0
        self.tick_remaining = len(steps) * 4  # ~4 ticks per step
        self.goal_desc = goal_desc

    def current_action(self):
        if self.is_complete():
            return None
        return self.steps[self.current_step]

    def advance(self):
        """Mark current step complete, move to next."""
        if self.current_step < len(self.steps):
            self.steps[self.current_step]["completed"] = True
        self.current_step += 1
        self.tick_remaining = max(1, self.tick_remaining)

    def is_complete(self):
        return self.current_step >= len(self.steps) or self.tick_remaining <= 0

    def summary(self):
        total = len(self.steps)
        cur = min(self.current_step, total)
        remaining = [s for s in self.steps[cur:] if not s.get("completed")]
        if not remaining:
            return "计划完成"
        next_step = remaining[0]
        return f"第{cur+1}/{total}步: {next_step.get('action_type','?')} → {next_step.get('target','?')}"

    def to_dict(self):
        return {
            "current_step": self.current_step,
            "total_steps": len(self.steps),
            "tick_remaining": self.tick_remaining,
            "summary": self.summary(),
            "steps": self.steps,
        }


# ═══════════════════════════════════════════════════════════════════════
# Belief System
# ═══════════════════════════════════════════════════════════════════════

BELIEF_DIMENSIONS = ['kindness', 'honesty', 'competence', 'reliability']
BELIEF_LABELS = {
    'kindness': '善良', 'honesty': '诚实',
    'competence': '能力', 'reliability': '可靠',
}


class Belief:
    __slots__ = ('about_id', 'kindness', 'honesty', 'competence',
                 'reliability', 'confidence', 'last_updated')

    def __init__(self, about_id, kindness=5, honesty=5, competence=5,
                 reliability=5, confidence=None):
        self.about_id = about_id
        self.kindness = kindness
        self.honesty = honesty
        self.competence = competence
        self.reliability = reliability
        self.confidence = confidence or {
            'kindness': 0.3, 'honesty': 0.3,
            'competence': 0.3, 'reliability': 0.3,
        }
        self.last_updated = 0

    def update(self, dimension, value, confidence, source="direct"):
        """Update a belief dimension with new information."""
        if dimension not in BELIEF_DIMENSIONS:
            return
        # Weighted update: higher source confidence = bigger shift
        weight = confidence
        if source == "gossip":
            weight *= 0.4
        elif source == "observation":
            weight *= 0.6
        current = getattr(self, dimension)
        new_val = current + (value - current) * weight
        setattr(self, dimension, max(0, min(10, new_val)))
        self.confidence[dimension] = min(1.0, self.confidence.get(dimension, 0.3) + 0.1)
        self.last_updated = int(time.time())

    def contradiction(self, observed_behavior):
        """Check if observations contradict beliefs. Returns list of contradictions."""
        contradictions = []
        for dim in BELIEF_DIMENSIONS:
            belief_val = getattr(self, dim)
            obs_val = observed_behavior.get(dim)
            if obs_val is not None and abs(belief_val - obs_val) >= 4:
                if self.confidence.get(dim, 0.3) > 0.5:
                    contradictions.append({
                        "dimension": dim,
                        "label": BELIEF_LABELS.get(dim, dim),
                        "believed": belief_val,
                        "observed": obs_val,
                        "gap": abs(belief_val - obs_val),
                    })
        return contradictions

    def summary(self):
        parts = []
        for dim in BELIEF_DIMENSIONS:
            v = getattr(self, dim)
            conf = self.confidence.get(dim, 0.3)
            label = "确信" if conf > 0.6 else "存疑" if conf < 0.4 else "一般"
            if v >= 6 or v <= 4:
                parts.append(f"{BELIEF_LABELS[dim]}{v:.0f}({label})")
        return " ".join(parts) if parts else "不了解"

    def to_dict(self):
        rounded_conf = {k: round(v, 1) for k, v in self.confidence.items()}
        return {
            "about_id": self.about_id,
            "dimensions": {
                dim: round(getattr(self, dim), 1) for dim in BELIEF_DIMENSIONS
            },
            "confidence": rounded_conf,
            "summary": self.summary(),
        }
