"""World map and agent presets for the pixel-town simulation."""

TILE_SIZE = 24
MAP_WIDTH = 40
MAP_HEIGHT = 31

# Tile types
GRASS = 0
WATER = 1
STONE = 2
FLOWERS = 3
BRIDGE = 4

# Color palette (for frontend reference)
TILE_COLORS = {
    GRASS: "#7ec850",
    WATER: "#4a8fcc",
    STONE: "#9e9588",
    FLOWERS: "#e870a0",
    BRIDGE: "#8b7355",
}

# 40x30 map — each character is one tile
# . = grass  ~ = water  # = stone path  * = flowers  = = bridge
MAP_LEGEND = {'.': GRASS, '~': WATER, '#': STONE, '*': FLOWERS, '=': BRIDGE, 'H': GRASS, 'T': GRASS, 'C': STONE, 'M': STONE, 'W': STONE, 'B': STONE}

_RAW = [
    "........................................",
    ".....###.......###...........###.......",
    ".HHH.#.#..TT...#.#...TT.....#.#..HHH..",
    ".HHH.#.#..TT...#.#...TT.....#.#..HHH..",
    ".HHH.###......###...........###..HHH..",
    ".....###......###...........###.......",
    "........TT..........TT................",
    "...**........****........**...........",
    "...**........****........**...........",
    "........TT................TT..........",
    "........................................",
    "....TT...TT....****....TT...TT........",
    "................**.....................",
    "........................................",
    "..........######..######...............",
    "..........#..C.#..#..M.#..............",
    "..........#....#..#....#..............",
    "..........######..######..............",
    "..........#..W.....#..................",
    "..........#........#..................",
    "..........###BB#####..................",
    "..............BB.......................",
    "........................................",
    "..~~~............TT.............~~~...",
    "..~~~...TT..................TT..~~~...",
    "..~~~.......TT..........TT.....~~~...",
    "..~~~..........................~~~...",
    "..~~~..........................~~~...",
    "..~~~~~~====================~~~~~~...",
    "..~~~~~~====================~~~~~~...",
    "........................................",
]

# Parse raw map into 2D integer grid (pad short rows to MAP_WIDTH)
WORLD_MAP = []
for row in _RAW:
    padded = row.ljust(MAP_WIDTH, '.')
    WORLD_MAP.append([MAP_LEGEND[c] for c in padded])

# Auto-generate tree objects from 'T' markers in the map
_AUTO_TREES = []
for _y, _row in enumerate(_RAW):
    for _x, _ch in enumerate(_row):
        if _ch == 'T':
            _AUTO_TREES.append({"id": f"tree_{_x}_{_y}", "name": "大树", "x": _x, "y": _y, "type": "tree"})

# Buildings / objects (tile coordinates)
# Each building occupies a rectangular area
BUILDINGS = [
    # Houses (top row)
    {"id": "house_1", "name": "小梅的家", "x": 1, "y": 2, "w": 3, "h": 3, "color": "#d4845a", "roof": "#b8402c"},
    {"id": "house_2", "name": "老王的屋子", "x": 19, "y": 2, "w": 3, "h": 3, "color": "#d4845a", "roof": "#4a6fa5"},
    {"id": "house_3", "name": "阿诗的住处", "x": 31, "y": 2, "w": 3, "h": 3, "color": "#d4845a", "roof": "#6b8c42"},
    # Central plaza buildings
    {"id": "market", "name": "集市", "x": 22, "y": 15, "w": 4, "h": 3, "color": "#e8c860", "roof": "#c4a040"},
    # Well (1 tile marker)
    {"id": "well", "name": "水井", "x": 11, "y": 18, "w": 1, "h": 1, "color": "#8b8b83", "roof": "#6b6b63"},
]

# Decorative objects (1 tile, non-blocking or blocking)
OBJECTS = [
    # Benches
    {"id": "bench_1", "name": "长椅", "x": 12, "y": 20, "type": "bench", "direction": "h"},
    {"id": "bench_2", "name": "长椅", "x": 13, "y": 20, "type": "bench", "direction": "h"},
    {"id": "bench_3", "name": "长椅", "x": 17, "y": 21, "type": "bench", "direction": "h"},
    {"id": "bench_4", "name": "长椅", "x": 18, "y": 21, "type": "bench", "direction": "h"},
    # Campfire
    {"id": "campfire", "name": "篝火", "x": 13, "y": 15, "type": "campfire"},
] + _AUTO_TREES

# Agent presets — 5 villagers with rich backstories
AGENTS = [
    {
        "id": "a1",
        "name": "小梅",
        "role": "村民",
        "x": 8, "y": 8,
        "home_x": 4, "home_y": 6,
        "personality": {"O": 0.7, "C": 0.6, "E": 0.85, "A": 0.9, "N": 0.55},
        "color": "#ff6b6b",
        "backstory": "21岁，在镇上长大的女孩。父母去了城里，她独自住在祖母留下的小屋里。表面乐观开朗，其实很害怕被抛弃。最近有点在意那个总在篝火旁唱歌的诗人阿诗，但不敢说出口。",
        "init_relationships": {
            "a3": {"affinity": 5.0, "tags": ["暗恋", "憧憬"], "memory": "阿诗唱歌的时候，整个世界都亮了"},
            "a4": {"affinity": 3.0, "tags": ["朋友"], "memory": "小石头虽然话少，但每次我难过他都默默陪着"},
            "a5": {"affinity": -1.0, "tags": ["有点烦"], "memory": "集市张总是吹牛，有点受不了"},
        },
        "init_relationships_2d": {
            "a3": {"trust": 4, "affection": 6, "respect": 6, "attraction": 7, "jealousy": 2, "resentment": 0,
                   "memory": "阿诗唱歌的时候，整个世界都亮了"},
            "a4": {"trust": 6, "affection": 5, "respect": 4, "attraction": 0, "jealousy": 0, "resentment": 0,
                   "memory": "小石头虽然话少，但每次我难过他都默默陪着"},
            "a5": {"trust": 3, "affection": 3, "respect": 2, "attraction": 0, "jealousy": 0, "resentment": 2,
                   "memory": "集市张总是吹牛，有点受不了"},
        },
        "init_beliefs": {
            "a3": {"kindness": 7, "honesty": 5, "competence": 8, "reliability": 4,
                   "confidence": {"kindness": 0.5, "honesty": 0.3, "competence": 0.7, "reliability": 0.3}},
            "a4": {"kindness": 8, "honesty": 7, "competence": 6, "reliability": 8,
                   "confidence": {"kindness": 0.8, "honesty": 0.7, "competence": 0.5, "reliability": 0.8}},
            "a5": {"kindness": 4, "honesty": 3, "competence": 6, "reliability": 5,
                   "confidence": {"kindness": 0.5, "honesty": 0.6, "competence": 0.5, "reliability": 0.4}},
        },
        "init_goals": [
            {"type": "romance", "description": "弄清楚阿诗对我到底是什么意思", "target": "a3", "priority": 9},
        ],
        "init_weighted_memories": [
            {"content": "阿诗唱歌的时候，整个世界都亮了", "importance": 8, "emotion": "happy",
             "related_agents": ["a3"], "unresolved": True},
            {"content": "集市张又在吹牛了，好烦", "importance": 4, "emotion": "annoyed",
             "related_agents": ["a5"], "unresolved": False},
        ],
    },
    {
        "id": "a2",
        "name": "老王",
        "role": "工匠",
        "x": 25, "y": 7,
        "home_x": 21, "home_y": 5,
        "personality": {"O": 0.35, "C": 0.9, "E": 0.25, "A": 0.6, "N": 0.65},
        "color": "#4ecdc4",
        "backstory": "58岁的鳏夫，做了一辈子木匠。妻子三年前病逝，孩子在大城市很少回来。他把所有时间都花在做工上，用忙碌掩盖孤独。偶尔会在长椅上发呆一整天。其实很想和人说说话，但不知道怎么开口。",
        "init_relationships": {
            "a1": {"affinity": 2.0, "tags": ["慈爱"], "memory": "小梅像他年轻时妻子的样子，让他感到温暖"},
            "a4": {"affinity": 1.5, "tags": ["尊重"], "memory": "小石头是唯一认真听他讲木匠经的人"},
        },
        "init_relationships_2d": {
            "a1": {"trust": 7, "affection": 6, "respect": 5, "attraction": 0, "jealousy": 0, "resentment": 0,
                   "memory": "小梅像他年轻时妻子的样子，让他感到温暖"},
            "a4": {"trust": 6, "affection": 4, "respect": 7, "attraction": 0, "jealousy": 0, "resentment": 0,
                   "memory": "小石头是唯一认真听他讲木匠经的人"},
        },
        "init_beliefs": {
            "a1": {"kindness": 8, "honesty": 7, "competence": 5, "reliability": 6,
                   "confidence": {"kindness": 0.8, "honesty": 0.7, "competence": 0.4, "reliability": 0.6}},
            "a4": {"kindness": 6, "honesty": 7, "competence": 8, "reliability": 7,
                   "confidence": {"kindness": 0.5, "honesty": 0.7, "competence": 0.8, "reliability": 0.7}},
        },
        "init_goals": [
            {"type": "work", "description": "专心做木匠活，用忙碌忘记孤独", "target": None, "priority": 6},
        ],
        "init_weighted_memories": [
            {"content": "小梅笑起来的样子真像她...", "importance": 8, "emotion": "sad",
             "related_agents": ["a1"], "unresolved": True},
        ],
    },
    {
        "id": "a3",
        "name": "阿诗",
        "role": "吟游诗人",
        "x": 35, "y": 12,
        "home_x": 33, "home_y": 5,
        "personality": {"O": 0.95, "C": 0.2, "E": 0.8, "A": 0.55, "N": 0.7},
        "color": "#ffe66d",
        "backstory": "25岁，流浪了三年后在这个小镇停下。去过很多地方，有很多故事，但从不说自己的过去。自由惯了，害怕被任何关系绑住。知道小梅对自己有意思，可是越是在意的人，越不敢靠近。",
        "init_relationships": {
            "a1": {"affinity": 3.5, "tags": ["在意", "愧疚"], "memory": "小梅的眼睛很亮，让我想起故乡的星空。但我配不上她"},
            "a5": {"affinity": -0.5, "tags": ["合不来"], "memory": "集市张总想收买我的故事去卖钱"},
        },
        "init_relationships_2d": {
            "a1": {"trust": 5, "affection": 6, "respect": 5, "attraction": 6, "jealousy": 0, "resentment": 0,
                   "memory": "小梅的眼睛很亮，让我想起故乡的星空。但我配不上她"},
            "a5": {"trust": 2, "affection": 3, "respect": 3, "attraction": 0, "jealousy": 0, "resentment": 1,
                   "memory": "集市张总想收买我的故事去卖钱"},
        },
        "init_beliefs": {
            "a1": {"kindness": 9, "honesty": 8, "competence": 5, "reliability": 6,
                   "confidence": {"kindness": 0.8, "honesty": 0.7, "competence": 0.4, "reliability": 0.5}},
            "a5": {"kindness": 4, "honesty": 3, "competence": 6, "reliability": 5,
                   "confidence": {"kindness": 0.5, "honesty": 0.6, "competence": 0.6, "reliability": 0.4}},
        },
        "init_goals": [
            {"type": "romance", "description": "不敢面对小梅的感情，想保持距离但又不舍得", "target": "a1", "priority": 8},
        ],
        "init_weighted_memories": [
            {"content": "小梅看我的眼神里有星星...但我习惯了流浪", "importance": 9, "emotion": "sad",
             "related_agents": ["a1"], "unresolved": True},
            {"content": "集市张想买我的故事，他不知道有些故事不能卖", "importance": 5, "emotion": "annoyed",
             "related_agents": ["a5"], "unresolved": False},
        ],
    },
    {
        "id": "a4",
        "name": "小石头",
        "role": "学者",
        "x": 5, "y": 22,
        "home_x": 3, "home_y": 6,
        "personality": {"O": 0.85, "C": 0.7, "E": 0.2, "A": 0.55, "N": 0.8},
        "color": "#a29bfe",
        "backstory": "19岁，镇上最年轻的读书人。社交恐惧，但观察力惊人——他能注意到每个人没说的话。偷偷记录着小镇上每个人的故事，已经写满了三个笔记本。一直纠结要不要把阿诗的秘密告诉小梅。",
        "init_relationships": {
            "a1": {"affinity": 3.0, "tags": ["友谊", "保护欲"], "memory": "小梅是唯一不嫌我说话慢的人"},
            "a2": {"affinity": 2.0, "tags": ["尊重"], "memory": "老王的手艺里藏着人生的道理"},
            "a3": {"affinity": 1.0, "tags": ["好奇", "怀疑"], "memory": "阿诗总是说一半藏一半，我知道她有秘密"},
        },
        "init_relationships_2d": {
            "a1": {"trust": 7, "affection": 6, "respect": 5, "attraction": 1, "jealousy": 0, "resentment": 0,
                   "memory": "小梅是唯一不嫌我说话慢的人"},
            "a2": {"trust": 6, "affection": 4, "respect": 8, "attraction": 0, "jealousy": 0, "resentment": 0,
                   "memory": "老王的手艺里藏着人生的道理"},
            "a3": {"trust": 3, "affection": 3, "respect": 5, "attraction": 0, "jealousy": 1, "resentment": 0,
                   "memory": "阿诗总是说一半藏一半，我知道她有秘密"},
        },
        "init_beliefs": {
            "a1": {"kindness": 9, "honesty": 8, "competence": 5, "reliability": 7,
                   "confidence": {"kindness": 0.9, "honesty": 0.8, "competence": 0.5, "reliability": 0.7}},
            "a2": {"kindness": 7, "honesty": 8, "competence": 9, "reliability": 8,
                   "confidence": {"kindness": 0.7, "honesty": 0.8, "competence": 0.9, "reliability": 0.8}},
            "a3": {"kindness": 5, "honesty": 3, "competence": 7, "reliability": 3,
                   "confidence": {"kindness": 0.4, "honesty": 0.5, "competence": 0.7, "reliability": 0.4}},
        },
        "init_goals": [
            {"type": "gossip_investigate", "description": "搞清楚阿诗到底在隐瞒什么秘密", "target": "a3", "priority": 7},
        ],
        "init_weighted_memories": [
            {"content": "阿诗对小梅说了谎——我不能确定，但我的笔记不会骗人", "importance": 8, "emotion": "anxious",
             "related_agents": ["a3", "a1"], "unresolved": True},
            {"content": "老王教我做榫卯结构，每一个细节都是人生智慧", "importance": 6, "emotion": "grateful",
             "related_agents": ["a2"], "unresolved": False},
        ],
    },
    {
        "id": "a5",
        "name": "集市张",
        "role": "商人",
        "x": 28, "y": 20,
        "home_x": 24, "home_y": 19,
        "personality": {"O": 0.5, "C": 0.75, "E": 0.9, "A": 0.35, "N": 0.45},
        "color": "#fd9644",
        "backstory": "35岁，在集市摆摊五年了。总是最大声吆喝的那个，用夸张的语气和永远讲不完的故事吸引顾客。小时候家里穷，被人看不起，所以拼命想证明自己。吹牛是他的盔甲。夜深人静的时候，一个人数钱其实很寂寞。",
        "init_relationships": {
            "a1": {"affinity": 1.0, "tags": ["欣赏"], "memory": "小梅是集市常客，总帮他尝新菜品"},
            "a2": {"affinity": 0.5, "tags": ["潜在客户"], "memory": "老王手艺好，想跟他合作卖家具"},
            "a3": {"affinity": -0.5, "tags": ["嫉妒"], "memory": "阿诗讲故事比我厉害，抢了我不少听众"},
        },
        "init_relationships_2d": {
            "a1": {"trust": 5, "affection": 4, "respect": 4, "attraction": 0, "jealousy": 0, "resentment": 0,
                   "memory": "小梅是集市常客，总帮他尝新菜品"},
            "a2": {"trust": 4, "affection": 3, "respect": 6, "attraction": 0, "jealousy": 0, "resentment": 0,
                   "memory": "老王手艺好，想跟他合作卖家具"},
            "a3": {"trust": 3, "affection": 2, "respect": 5, "attraction": 0, "jealousy": 6, "resentment": 2,
                   "memory": "阿诗讲故事比我厉害，抢了我不少听众"},
        },
        "init_beliefs": {
            "a1": {"kindness": 7, "honesty": 6, "competence": 5, "reliability": 6,
                   "confidence": {"kindness": 0.6, "honesty": 0.5, "competence": 0.4, "reliability": 0.5}},
            "a2": {"kindness": 5, "honesty": 5, "competence": 9, "reliability": 7,
                   "confidence": {"kindness": 0.4, "honesty": 0.4, "competence": 0.8, "reliability": 0.7}},
            "a3": {"kindness": 5, "honesty": 5, "competence": 8, "reliability": 4,
                   "confidence": {"kindness": 0.5, "honesty": 0.4, "competence": 0.8, "reliability": 0.3}},
        },
        "init_goals": [
            {"type": "work", "description": "在集市上成为最受欢迎的摊主", "target": None, "priority": 7},
        ],
        "init_weighted_memories": [
            {"content": "阿诗又抢了我的听众，但我必须承认她确实有才华", "importance": 6, "emotion": "jealous",
             "related_agents": ["a3"], "unresolved": True},
        ],
    },
]
