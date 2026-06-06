# 像素小镇 — Multi-Agent Social Simulation

一个像素风的 2D 小镇，3-5 个 LLM 驱动的 AI Agent 各自有性格和目标，在小镇上自由生活、互动、社交。

## 运行

```bash
# 安装依赖
pip install -r requirements.txt

# 启动 (确保 Ollama 在本地运行且有模型)
python main.py

# 浏览器打开
# http://localhost:8000
```

## 技术栈

- **后端**: FastAPI + WebSocket + asyncio
- **前端**: Canvas 2D 像素渲染引擎
- **AI**: Ollama 本地 LLM（支持 qwen2.5 / llama3.1 等）

## Agent 系统

每个 Agent 有独立的大五人格、角色设定和记忆系统。每个 tick：
1. 感知周围环境（6格范围内的角色和物体）
2. 调用 LLM 根据性格+感知+记忆做决策
3. 执行动作（移动/说话/互动/发呆）

## 项目结构

```
├── main.py        # 入口
├── server.py      # FastAPI + WebSocket
├── world.py       # 世界网格、碰撞、BFS 寻路
├── agent.py       # Agent 类
├── llm.py         # Ollama 客户端 + Mock 模式
├── config.py      # 地图、建筑、Agent 预设
└── static/
    └── index.html # 像素渲染引擎 + UI
```
