"""Ollama LLM client — prompts that evoke human-like behavior."""

import json
import re

try:
    import httpx
    _HAS_HTTPX = True
except ImportError:
    _HAS_HTTPX = False

SYSTEM_PROMPT = """你是像素小镇上的一个有血有肉的人。

你的行为要符合你的性格、角色设定、当前情绪和身体需求。
你必须只回复一个 JSON 对象。

JSON格式:
{"action":"move"|"speak"|"interact"|"idle","target":"目标名称","text":"说的话","thought":"内心独白","gossip_about":"可选的第三方名字"}

关于 gossip_about: 聊天时可以八卦其他角色，比如"我觉得老王最近怪怪的"，就把 gossip_about 填"老王"

你的人性化准则:
- 你会有情绪波动: 开心时话多，难过时沉默，生气时说话带刺
- 身体需求影响行为: 饿了觅食，累了找地方休息，孤独了找人倾诉
- 你对不同人有不同态度: 对喜欢的人温柔，对讨厌的人冷淡
- 你会记住别人对你的好和坏，态度会积累变化
- 你偶尔会脆弱、矛盾、口是心非——这才是真实的人
- 对话要自然，像真实聊天，不要说教

规则:
- 每回合最多移动3-5格
- speak时text必须写一句中文对话(10-30字)
- 如果选择speak且想聊到第三方，填gossip_about
- 保持角色一致性"""


class LLMClient:
    def __init__(self, base_url="http://localhost:11434", model="qwen2.5:7b"):
        self.base_url = base_url
        self.model = model

    async def decide(self, agent_state, perception):
        if not _HAS_HTTPX:
            return {"action": "idle", "target": "", "text": "", "thought": "httpx未安装"}

        user_prompt = self._build_prompt(agent_state, perception)

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
                return self._parse_response(content)
            except Exception as e:
                print(f"[LLM error] {e}")
                return {"action": "idle", "target": "", "text": "", "thought": "连接失败..."}

    def _build_prompt(self, agent, perception):
        p = agent["personality"]
        n = agent.get("needs", {})
        lines = [
            f"你是{agent['name']}，一个{agent['role']}。",
            f"你的故事: {agent['backstory']}",
            f"性格: 开放{p['O']:.0%} 尽责{p['C']:.0%} 外向{p['E']:.0%} 宜人{p['A']:.0%} 神经质{p['N']:.0%}",
            f"当前目标: {agent.get('current_goal', '探索小镇')}",
            f"位置: ({agent['x']}, {agent['y']})",
            "",
            f"【你的情绪】{agent.get('emotion', '平静')}",
            f"【身体需求】饥饿{n.get('hunger',50):.0f}/100 社交{n.get('social',50):.0f}/100 疲劳{n.get('rest',50):.0f}/100 意义{n.get('purpose',50):.0f}/100",
            f"当前最缺: {n.get('lowest','?')}",
        ]

        rels = agent.get("relationships", [])
        if rels:
            lines.append("")
            lines.append("【你的人际关系】")
            for r in rels:
                lines.append(f"  {r}")

        gossip = agent.get("gossip_heard", [])
        if gossip:
            lines.append("")
            lines.append("【你听说的流言】")
            for g in gossip:
                lines.append(f"  - {g}")

        if agent.get("memory"):
            lines.append("")
            lines.append("【最近的个人记忆】")
            for m in agent["memory"][-5:]:
                lines.append(f"  - {m}")

        nearby = perception.get("nearby_agents", [])
        if nearby:
            lines.append("")
            lines.append("【附近的人】")
            for a in nearby:
                lines.append(f"  {a['name']}({a['role']}) 距离{a['distance']}格")

        nearby_obj = perception.get("nearby_objects", [])
        if nearby_obj:
            lines.append("")
            lines.append("【附近的物体/建筑】")
            for o in nearby_obj[:5]:
                name = o.get('name', o.get('type', '?'))
                lines.append(f"  {name} 距离{o['distance']}格")

        lines.append("")
        lines.append("基于你现在的情绪、需求和人际关系，你想做什么？回复JSON:")
        return "\n".join(lines)

    def _parse_response(self, content):
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            pass

        json_match = re.search(r'\{[^{}]*"action"[^{}]*\}', content, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass

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

        return {"action": action, "target": target, "text": text, "thought": thought, "gossip_about": gossip_about}


class MockLLMClient:
    """Rich mock: emotion-aware behavior without real LLM."""

    async def decide(self, agent_state, perception):
        import random
        nearby = perception.get("nearby_agents", [])
        emotion = agent_state.get("emotion", "平静")
        needs = agent_state.get("needs", {})
        lowest = needs.get("lowest", "social")
        r = random.random()

        # Driven by lowest need
        if lowest == "social" and nearby and r < 0.5:
            target = random.choice(nearby)
            tone = "开心地" if "happy" in emotion or "excited" in emotion else \
                   "疲惫地" if "anxious" in emotion else \
                   "小心翼翼地" if "lonely" in emotion else ""
            phrases = {
                "lonely": [f"{tone}说: 能陪我说说话吗...", f"{tone}说: 有时候觉得好孤单啊"],
                "happy": [f"{tone}说: 嘿！今天真不错！", f"{tone}说: 哈哈哈你说得对"],
                "sad": [f"{tone}说: 唉...今天不太顺", f"{tone}说: 有些事让人难过"],
                "angry": [f"{tone}说: 我受够了！", f"{tone}说: 别跟我提那个人"],
                "default": [f"{tone}说: 你最近怎么样？", f"{tone}说: 这小镇真平静啊"],
            }
            etype = agent_state.get("emotion", "").split("(")[0] if "(" in emotion else "calm"
            choices = phrases.get(etype, phrases["default"])
            text = random.choice(choices).replace("{tone}说: ", "")

            # Maybe gossip
            gossip_about = ""
            if random.random() < 0.25:
                others = [a for a in nearby if a["name"] != target["name"]]
                if others:
                    g = random.choice(others)
                    gossip_about = g["name"]
                    if random.random() < 0.5:
                        text = f"我觉得{g['name']}人挺好的"
                    else:
                        text = f"你有没有觉得{g['name']}最近有点怪？"

            return {
                "action": "speak", "target": target["name"],
                "text": text, "thought": f"想和{target['name']}说说话",
                "gossip_about": gossip_about,
            }

        elif lowest == "hunger" and r < 0.4:
            return {"action": "move", "target": "集市", "text": "", "thought": "肚子饿了，去集市找吃的", "gossip_about": ""}

        elif lowest == "rest" and r < 0.5:
            places = ["长椅", "小梅的家", "老王的屋子", "阿诗的住处"]
            return {"action": "move", "target": random.choice(places), "text": "",
                    "thought": "好累，想找个地方歇歇", "gossip_about": ""}

        elif lowest == "purpose" and r < 0.4:
            return {"action": "move", "target": random.choice(["篝火", "集市", "水井"]),
                    "text": "", "thought": "想做点有意思的事...", "gossip_about": ""}

        elif nearby and r < 0.3:
            target = random.choice(nearby)
            return {"action": "move", "target": target["name"], "text": "", "thought": f"靠近{target['name']}", "gossip_about": ""}

        else:
            thoughts = {
                "lonely": ["有点孤单...", "希望能遇到谁"],
                "happy": ["心情不错", "今天天气也好"],
                "sad": ["提不起劲...", "想一个人静静"],
                "anxious": ["有点不安", "需要缓缓"],
                "default": ["放空一下", "看看远处", "发会儿呆"],
            }
            etype = agent_state.get("emotion", "").split("(")[0] if "(" in emotion else "calm"
            t = random.choice(thoughts.get(etype, thoughts["default"]))
            return {"action": "idle", "target": "", "text": "", "thought": t, "gossip_about": ""}
