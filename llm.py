"""LLM clients — DeepSeek API, Ollama, and Mock fallback."""

import json
import re
import os

try:
    import httpx
    _HAS_HTTPX = True
except ImportError:
    _HAS_HTTPX = False

SYSTEM_PROMPT = """你是像素小镇上的一个有深层内心世界的人。你不只是"选动作"——你有长期目标、复杂情感、对别人的信念、和未解开的心结。

你必须只回复一个 JSON 对象，格式:
{"action":"move"|"speak"|"interact"|"idle","target":"目标名称","text":"说的话","thought":"内心独白","gossip_about":"可选的第三方名字"}

===== 你的内心架构（8层动机系统）=====

【第1层：多维关系】你对每个人的感觉不只是"好/坏"。你有6个维度：
- 信任：你有多相信这个人
- 好感：你有多喜欢这个人
- 尊敬：你有多尊重这个人
- 吸引：浪漫/性的吸引力
- 嫉妒：你有多嫉妒这个人
- 怨恨：你心里积了多少对这个人的怨
这些维度共同决定你和对方的关系阶段（陌生人→认识→朋友→密友→暗恋→恋人→敌人→对手）

【第2层：加权记忆】你的记忆不是等价的。重要的记忆（标记⚡的未解决记忆）应该优先影响你的行为。不要反复纠结不重要的小事。

【第3层：目标→计划→行动】你有长期目标（持续多个回合），每个目标分解为短期计划（3-5步）。不要每回合换一个目标——坚持你的目标直到完成或被更重要的事打断。但也要灵活：如果突然有人对你说话、或发生了特别的事，可以临时调整。

【第4层：关系阶段】不同阶段有不同的行为：
- 对暗恋对象：说话温柔但可能紧张，想靠近又不敢太明显
- 对密友：可以开玩笑、倾诉心事
- 对敌人：回避、阴阳怪气、或直接冲突
- 对对手：暗暗较劲但保持礼貌

【第5层：开放循环】标记⚡的未解决记忆是你心里的"疙瘩"。你应该主动尝试解决它们——去找相关的人问清楚、或者通过行动来验证。不要让它们一直悬着。

【第6层：流言可信度】你听到的流言不一定要全信。你会根据说话人的可信度、流言本身的合理性、以及你和被谈论者的关系来判断该信几分。

【第7层：情绪惰性】你的情绪不会瞬间切换。如果你正在生气，不会下一秒就开心起来。强烈的情绪会"残留"几个回合，慢慢消退。这让你更像真实的人。

【第8层：信念系统】你对每个人有一套内在看法（善良、诚实、能力、可靠），这些看法来自直接交往和流言。当你的信念和观察到的行为冲突时，你会困惑——而这本身可以成为行动的动力。

===== 行为准则 =====
- 坚持你的长期目标！如果目标是"弄清楚阿诗的心思"，那你应该去找阿诗说话，而不是突然去集市买菜
- 对话丰富多变——聊感情、聊八卦、聊心事、聊过去、关心对方、开玩笑
- 情绪驱动行为：愤怒时说带刺的话，孤独时主动找人，开心时话多
- 因人而异：对好感度高的人温柔，对讨厌的人冷淡
- 口是心非是允许的：明明在意却假装不在乎
- 每回合最多移动3-5格
- 附近有人(距离<=3格)时优先对话
- speak时text写一句中文对话(10-30字)，自然不做作
- 想聊到第三方时填gossip_about
- 让你的行为有变化——不要连续做同样的事
- 每回合问自己：我上次做了什么？这次换个不一样的"""


def _build_prompt(agent_state, perception):
    p = agent_state.get("personality", {})
    name = agent_state.get("name", "?")

    # Personality voice hints
    voice_hints = []
    if p.get('E', 0.5) > 0.7:
        voice_hints.append("你话多外向，喜欢主动找人聊天，说话直来直去")
    elif p.get('E', 0.5) < 0.3:
        voice_hints.append("你话少内向，说话前会犹豫，但一旦开口往往一针见血")
    else:
        voice_hints.append("你跟熟人话多，跟陌生人话少，看心情")

    if p.get('A', 0.5) > 0.7:
        voice_hints.append("你说话温柔体贴，不爱冲突，经常安慰别人")
    elif p.get('A', 0.5) < 0.35:
        voice_hints.append("你说话直接甚至刻薄，不怕得罪人，偶尔阴阳怪气")

    if p.get('N', 0.5) > 0.65:
        voice_hints.append("你容易焦虑多想，说话时常常透露出不安或纠结")
    elif p.get('N', 0.5) < 0.4:
        voice_hints.append("你心态稳，遇事淡定，说话从容不迫")

    if p.get('O', 0.5) > 0.8:
        voice_hints.append("你想象力丰富，说话喜欢用比喻，有时候思维跳跃")
    elif p.get('O', 0.5) < 0.4:
        voice_hints.append("你务实传统，说话接地气，不喜欢绕弯子")

    lines = [
        f"你是{name}，一个{agent_state.get('role', '村民')}。",
        f"你的故事: {agent_state.get('backstory', '')}",
        f"性格: 开放{p.get('O',0.5):.0%} 尽责{p.get('C',0.5):.0%} 外向{p.get('E',0.5):.0%} 宜人{p.get('A',0.5):.0%} 神经质{p.get('N',0.5):.0%}",
        f"【你的说话风格】{'；'.join(voice_hints)}",
        "",
    ]

    # ─── Layer 3: Goal & Plan ───
    goal = agent_state.get("goal")
    plan = agent_state.get("plan")
    if goal:
        pct = goal.get("progress", 0) / max(goal.get("max_progress", 100), 1) * 100
        lines.append(f"🎯【长期目标】{goal.get('label','')}: {goal.get('description','')}（进度{pct:.0f}%）")
    if plan and plan.get("summary"):
        lines.append(f"📋【当前计划】{plan['summary']}")

    # ─── Layer 7: Mood Vector ───
    mv = agent_state.get("mood_vector", {})
    dominant = agent_state.get("dominant_mood", "calm")
    label = agent_state.get("mood_label", "平静")
    lingering = mv.get("lingering", [])
    lines.append("")
    lines.append(f"💭【情绪状态】{label}（主导: {dominant}）")
    lines.append(f"   愉悦{mv.get('happiness',5):.0f} 悲伤{mv.get('sadness',1):.0f} 焦虑{mv.get('anxiety',2):.0f} 愤怒{mv.get('anger',0):.0f} 孤独{mv.get('loneliness',3):.0f}")
    if lingering:
        lines.append(f"   ⚡残留情绪: {', '.join(lingering)}（正在缓慢消退中）")

    # ─── Needs ───
    needs = agent_state.get("needs", {})
    lowest = agent_state.get("needs_lowest", "social")
    lines.append(f"📊【需求】饥饿{needs.get('hunger',50):.0f} 社交{needs.get('social',50):.0f} 疲劳{needs.get('rest',50):.0f} 意义{needs.get('purpose',50):.0f}（最缺: {lowest}）")

    # ─── Layer 1: Multi-dimensional Relationships ───
    rels = agent_state.get("relationships", [])
    if rels:
        lines.append("")
        lines.append("❤️【多维关系】")
        for r in rels:
            dims = r.get("dimensions", {})
            stage_label = r.get("stage_label", "?")
            stage_emoji = r.get("stage_emoji", "")
            name_r = r.get("name", "?")
            dims_str = " ".join(
                f"{k}={v:.0f}" for k, v in dims.items() if v >= 4
            )
            tags = r.get("tags", [])
            tags_str = f" [{','.join(tags)}]" if tags else ""
            lines.append(f"  {stage_emoji}{name_r} → {stage_label}{tags_str}")
            if dims_str:
                lines.append(f"    维度: {dims_str}")

    # ─── Layer 8: Beliefs ───
    beliefs = agent_state.get("beliefs", {})
    if beliefs:
        lines.append("")
        lines.append("🧠【对他人的信念】")
        for rid, b in beliefs.items():
            summary = b.get("summary", "")
            if summary and summary != "不了解":
                # Find name
                bname = rid
                for r in rels:
                    if r.get("name") and r in agent_state.get("relationships", []):
                        pass
                lines.append(f"  对{rid}: {summary}")

    # ─── Layer 2: Weighted Memories (top 5) ───
    top_mems = agent_state.get("top_memories", [])
    if top_mems:
        lines.append("")
        lines.append("📝【重要记忆】")
        for m in top_mems[:5]:
            lines.append(f"  {m}")

    # ─── Layer 5: Open Loops (unresolved) ───
    unresolved = agent_state.get("unresolved_memories", [])
    if unresolved:
        lines.append("")
        lines.append("⚡【未解心结——你应该优先处理这些！】")
        for m in unresolved:
            lines.append(f"  {m}")

    # ─── Gossip ───
    gossip = agent_state.get("gossip_heard", [])
    if gossip:
        lines.append("")
        lines.append("🗣【听说的流言】")
        for g in gossip:
            lines.append(f"  - {g}")

    # ─── Recent speech directed at me ───
    recent_speech = perception.get("recent_speech", [])
    if recent_speech:
        lines.append("")
        lines.append("🔔【刚才有人跟你说话了！你必须回应！】")
        for s in recent_speech:
            lines.append(f"  {s['from_name']}对你说: \"{s['text']}\"")
        lines.append("你应该回应对方——可以接着聊、表示认同、提出疑问、或者表达你的感受。")

    # ─── Nearby ───
    nearby = perception.get("nearby_agents", [])
    if nearby:
        lines.append("")
        lines.append("👥【附近的人】")
        for a in nearby:
            lines.append(f"  {a['name']}({a['role']}) 距离{a.get('distance','?')}格")

    nearby_obj = perception.get("nearby_objects", [])
    if nearby_obj:
        lines.append("")
        lines.append("📍【附近地点】")
        for o in nearby_obj[:5]:
            obj_name = o.get('name', o.get('type', '?'))
            lines.append(f"  {obj_name} 距离{o.get('distance','?')}格")

    # ─── Decision guidance ───
    lines.append("")
    lines.append("【决策指南】")
    lines.append("- 1) 首先看有没有未解心结(⚡)需要处理 → 优先行动")
    lines.append("- 2) 其次看你的长期目标(🎯) → 坚持推进")
    lines.append("- 3) 再看有没有人刚跟你说话(🔔) → 必须回应")
    lines.append("- 4) 考虑你的情绪状态和周围环境")
    lines.append("- 5) 让你的行为有变化——别一直做同样的事")
    lines.append("")
    lines.append("回复JSON:")

    return "\n".join(lines)


def _parse_response(content):
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        pass

    # Try to extract JSON from markdown code blocks
    block_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', content, re.DOTALL)
    if block_match:
        try:
            return json.loads(block_match.group(1))
        except json.JSONDecodeError:
            pass

    # Try bare JSON with balanced braces
    brace_count = 0
    start = -1
    for i, ch in enumerate(content):
        if ch == '{':
            if brace_count == 0:
                start = i
            brace_count += 1
        elif ch == '}':
            brace_count -= 1
            if brace_count == 0 and start >= 0:
                try:
                    return json.loads(content[start:i+1])
                except json.JSONDecodeError:
                    start = -1
                    continue

    action = "idle"
    target = ""
    text = ""
    thought = content[:50]
    gossip_about = ""

    if "move" in content.lower():
        action = "move"
    elif "speak" in content.lower() or "说" in content:
        action = "speak"
        text_match = re.search(r'"text"\s*:\s*"([^"]*)"', content)
        if text_match:
            text = text_match.group(1)
        gossip_match = re.search(r'"gossip_about"\s*:\s*"([^"]*)"', content)
        if gossip_match:
            gossip_about = gossip_match.group(1)
    elif "interact" in content.lower():
        action = "interact"

    return {"action": action, "target": target, "text": text,
            "thought": thought, "gossip_about": gossip_about}


class DeepSeekClient:
    """DeepSeek API (OpenAI-compatible). Set DEEPSEEK_API_KEY env var."""

    def __init__(self, api_key=None, model="deepseek-chat"):
        self.api_key = api_key or os.environ.get("DEEPSEEK_API_KEY", "")
        self.model = model
        self.base_url = "https://api.deepseek.com/v1/chat/completions"

    async def decide(self, agent_state, perception):
        if not self.api_key:
            print("[DeepSeek] DEEPSEEK_API_KEY not set")
            return {"action": "idle", "target": "", "text": "",
                    "thought": "API key没设置..."}

        if not _HAS_HTTPX:
            return {"action": "idle", "target": "", "text": "",
                    "thought": "httpx未安装"}

        user_prompt = _build_prompt(agent_state, perception)

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                resp = await client.post(
                    self.base_url,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self.model,
                        "messages": [
                            {"role": "system", "content": SYSTEM_PROMPT},
                            {"role": "user", "content": user_prompt},
                        ],
                        "temperature": 1.05,
                        "max_tokens": 500,
                        "stream": False,
                    },
                )
                resp.raise_for_status()
                data = resp.json()
                content = data["choices"][0]["message"]["content"]
                result = _parse_response(content)
                print(f"[DeepSeek] {agent_state.get('name','?')} → "
                      f"{result.get('action','?')}: "
                      f"{result.get('text','')[:30] or result.get('thought','')[:30]}")
                return result
            except Exception as e:
                print(f"[DeepSeek error] {e}")
                return {"action": "idle", "target": "", "text": "",
                        "thought": "API调用失败..."}


class LLMClient:
    """Ollama local client."""

    def __init__(self, base_url="http://localhost:11434", model="qwen2.5:7b"):
        self.base_url = base_url
        self.model = model

    async def decide(self, agent_state, perception):
        if not _HAS_HTTPX:
            return {"action": "idle", "target": "", "text": "",
                    "thought": "httpx未安装"}

        user_prompt = _build_prompt(agent_state, perception)

        async with httpx.AsyncClient(timeout=25.0) as client:
            try:
                resp = await client.post(
                    f"{self.base_url}/api/chat",
                    json={
                        "model": self.model,
                        "messages": [
                            {"role": "system", "content": SYSTEM_PROMPT},
                            {"role": "user", "content": user_prompt},
                        ],
                        "stream": False,
                        "options": {"temperature": 0.85, "num_predict": 256},
                    },
                )
                resp.raise_for_status()
                content = resp.json()["message"]["content"]
                return _parse_response(content)
            except Exception as e:
                print(f"[LLM error] {e}")
                return {"action": "idle", "target": "", "text": "",
                        "thought": "连接失败..."}


class MockLLMClient:
    """Rich mock: goal-aware and mood-driven behavior without real LLM."""

    async def decide(self, agent_state, perception):
        import random
        nearby = perception.get("nearby_agents", [])
        mood_label = agent_state.get("mood_label", "平静")
        dominant = agent_state.get("dominant_mood", "calm")
        unresolved = agent_state.get("unresolved_memories", [])
        goal = agent_state.get("goal", {})
        r = random.random()

        # Priority 0: unresolved memories involving nearby agents
        if unresolved and nearby and r < 0.5:
            for mem in unresolved[:2]:
                # Try to find a nearby agent to talk to about the unresolved issue
                target = random.choice(nearby)
                text = random.choice([
                    f"我最近一直在想一件事...{mem[:20]}",
                    f"你有时间吗？我想跟你聊聊一些心事",
                    f"有些事憋在心里好久了，能听我说说吗？",
                ])
                return {
                    "action": "speak", "target": target["name"],
                    "text": text,
                    "thought": f"想找人说说话，解开心里的疙瘩",
                    "gossip_about": "",
                }

        # Priority 1: goal-driven action
        goal_type = goal.get("type", "")
        goal_target = goal.get("target_agent_id", "")

        if goal_type == "romance" and nearby and r < 0.6:
            # Find the romantic target or talk about feelings
            for a in nearby:
                if a["name"] == goal_target or r < 0.3:
                    phrases = [
                        f"你最近...还好吗？", f"有些话我一直想跟你说...",
                        f"你唱歌的时候，我总觉得时间过得好慢",
                        f"没什么...就是想听听你的声音",
                        f"今天的天气真好，想跟你一起走走",
                    ]
                    return {
                        "action": "speak", "target": a["name"],
                        "text": random.choice(phrases),
                        "thought": f"想靠近{target['name'] if target else 'ta'}，又有点紧张",
                        "gossip_about": "",
                    }

        if goal_type == "socialize" and nearby and r < 0.55:
            target = random.choice(nearby)
            phrases = {
                'happiness': ["嘿！今天真不错！", "哈哈哈你说得对", "天气真好，心情也好"],
                'sadness': ["唉...最近有些事让人难过", "有时候真不知道该怎么办"],
                'anger': ["有些事真的让人生气", "你听说了吗？那事太过分了"],
                'anxiety': ["最近总觉得有点不安", "你说未来会怎么样呢？"],
                'loneliness': ["能陪我说说话吗...", "有时候觉得好孤单啊", "你今天有空吗？"],
            }
            texts = phrases.get(dominant, ["你最近怎么样？", "今天过得如何？", "想跟你聊聊"])
            text = random.choice(texts)

            gossip_about = ""
            if random.random() < 0.35:
                others = [a for a in nearby if a["name"] != target["name"]]
                if others:
                    g = random.choice(others)
                    gossip_about = g["name"]

            return {
                "action": "speak", "target": target["name"],
                "text": text, "thought": f"想和{target['name']}聊聊",
                "gossip_about": gossip_about,
            }

        # Priority 2: need-driven
        needs = agent_state.get("needs", {})
        if needs.get("rest", 50) < 30 and r < 0.5:
            dest = random.choice(["长椅", "小梅的家", "老王的屋子", "阿诗的住处", "篝火"])
            return {"action": "move", "target": dest, "text": "",
                    "thought": "有点累了，找个地方歇歇"}

        if needs.get("hunger", 50) < 30 and r < 0.4:
            return {"action": "move", "target": "集市", "text": "",
                    "thought": "顺路去集市看看"}

        # Priority 3: exploration / idle
        if nearby and r < 0.7:
            target = random.choice(nearby)
            return {"action": "move", "target": target["name"], "text": "",
                    "thought": f"靠近{target['name']}，看看ta在做什么"}

        spots = ["篝火", "集市", "水井", "长椅"]
        return {"action": "move", "target": random.choice(spots), "text": "",
                "thought": random.choice(["放空一下", "四处看看", "享受片刻的宁静"])}
