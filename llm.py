"""Ollama LLM client for agent decision-making."""

import json
import re

try:
    import httpx
    _HAS_HTTPX = True
except ImportError:
    _HAS_HTTPX = False

SYSTEM_PROMPT = """你是一个像素小镇上的角色。你的行为要符合你的性格和角色设定。
你必须只回复一个 JSON 对象，不要有任何额外文字。

JSON 格式:
{"action": "move"|"speak"|"interact"|"idle", "target": "目标描述或坐标", "text": "说的话(仅speak时)", "thought": "你的内心想法"}

可选动作说明:
- move: 走向一个目标(其他角色、建筑、物体)，target填目标名称如"篝火"、"集市"、"小梅"
- speak: 对附近的某个角色说话，target填对方名字，text填说话内容
- interact: 与物体互动(坐在长椅上、在水井打水、逛集市等)，target填物体名称
- idle: 原地休息/发呆/看风景

规则:
- 每回合最多移动3-5格
- 如果附近有其他角色，优先考虑互动或对话
- 对话要简短自然(一句中文，不超过20字)
- 如果选择speak，text必须有对话内容
- 保持角色一致性，不要突然性格大变
"""


class LLMClient:
    def __init__(self, base_url="http://localhost:11434", model="qwen2.5:7b"):
        self.base_url = base_url
        self.model = model

    async def decide(self, agent_state, perception):
        """Send agent state + perception to LLM, return parsed action dict."""
        if not _HAS_HTTPX:
            return {"action": "idle", "target": "", "text": "", "thought": "（httpx未安装）"}
        user_prompt = self._build_prompt(agent_state, perception)

        async with httpx.AsyncClient(timeout=20.0) as client:
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
                        "options": {
                            "temperature": 0.8,
                            "num_predict": 200,
                        },
                    },
                )
                resp.raise_for_status()
                data = resp.json()
                content = data["message"]["content"]
                return self._parse_response(content)
            except Exception as e:
                print(f"[LLM error] {e}")
                return {
                    "action": "idle",
                    "target": "",
                    "text": "",
                    "thought": "（脑子有点乱...）",
                }

    def _build_prompt(self, agent, perception):
        p = agent["personality"]
        parts = [
            f"你是{agent['name']}，一个{agent['role']}。",
            f"性格: 开放性{p['O']:.0%} 尽责性{p['C']:.0%} 外向性{p['E']:.0%} 宜人性{p['A']:.0%} 神经质{p['N']:.0%}",
            f"背景: {agent['backstory']}",
            f"当前目标: {agent.get('current_goal', '到处走走')}",
            f"位置: ({agent['x']}, {agent['y']})",
        ]

        if agent.get("memory"):
            memories = agent["memory"][-5:]
            parts.append("最近的记忆:")
            for m in memories:
                parts.append(f"  - {m}")

        nearby = perception.get("nearby_agents", [])
        if nearby:
            parts.append("附近的角色:")
            for a in nearby:
                parts.append(f"  - {a['name']}({a['role']}) 距离{a['distance']}格")

        nearby_obj = perception.get("nearby_objects", [])
        if nearby_obj:
            parts.append("附近的物体/建筑:")
            for o in nearby_obj[:5]:
                parts.append(f"  - {o.get('name', o.get('type', '?'))} 距离{o['distance']}格")

        parts.append("\n现在你要做什么？回复JSON:")
        return "\n".join(parts)

    def _parse_response(self, content):
        """Extract JSON from LLM response, with fallback."""
        # Try direct JSON parse
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            pass

        # Try to find JSON block
        json_match = re.search(r'\{[^{}]*"action"[^{}]*\}', content, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass

        # Fallback: parse heuristically
        action = "idle"
        target = ""
        text = ""
        thought = content[:50]

        if "move" in content.lower():
            action = "move"
        elif "speak" in content.lower() or "说" in content:
            action = "speak"
            # Try to extract text
            text_match = re.search(r'"text"\s*:\s*"([^"]*)"', content)
            if text_match:
                text = text_match.group(1)
        elif "interact" in content.lower() or "互动" in content:
            action = "interact"
        elif "idle" in content.lower() or "发呆" in content or "休息" in content:
            action = "idle"

        return {
            "action": action,
            "target": target,
            "text": text,
            "thought": thought,
        }


class MockLLMClient:
    """Mock client for testing without Ollama. Agents wander and chat randomly."""

    async def decide(self, agent_state, perception):
        import random
        nearby = perception.get("nearby_agents", [])
        r = random.random()

        if nearby and r < 0.35:
            target = random.choice(nearby)
            greetings = [
                "今天天气真好！", "你吃饭了吗？", "嗨！最近怎么样？",
                "有没有什么新鲜事？", "今天集市上挺热闹的。",
                "你看起来心情不错！", "要不要一起去篝火那边？",
                "这小镇真安逸啊。", "你听说什么有趣的事了吗？",
                "嘿，好久不见！",
            ]
            return {
                "action": "speak",
                "target": target["name"],
                "text": random.choice(greetings),
                "thought": f"看到{target['name']}了，去打个招呼",
            }
        elif nearby and r < 0.55:
            target = random.choice(nearby)
            return {
                "action": "move",
                "target": target["name"],
                "text": "",
                "thought": f"想靠近{target['name']}看看",
            }
        elif r < 0.35:
            objects = perception.get("nearby_objects", [])
            if objects:
                obj = random.choice(objects)
                name = obj.get("name", obj.get("type", "那里"))
                return {
                    "action": "move",
                    "target": name,
                    "text": "",
                    "thought": f"去{name}那边",
                }
            return {"action": "move", "target": "四处走走", "text": "", "thought": "随便逛逛"}
        else:
            thoughts = ["放空一下...", "看看风景", "有点累了", "今天过得不错", "想想接下来干嘛"]
            return {
                "action": "idle",
                "target": "",
                "text": "",
                "thought": random.choice(thoughts),
            }
