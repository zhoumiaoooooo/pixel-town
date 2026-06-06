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

# Parse raw map into 2D integer grid
WORLD_MAP = [[MAP_LEGEND[c] for c in row] for row in _RAW]

# Auto-generate tree objects from 'T' markers in the map
_AUTO_TREES = []
for _y, _row in enumerate(_RAW):
    for _x, _ch in enumerate(_row):
        if _ch == 'T':
            _AUTO_TREES.append({"id": f"tree_{_x}_{_y}", "x": _x, "y": _y, "type": "tree"})

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
    {"id": "bench_1", "x": 12, "y": 20, "type": "bench", "direction": "h"},
    {"id": "bench_2", "x": 13, "y": 20, "type": "bench", "direction": "h"},
    {"id": "bench_3", "x": 17, "y": 21, "type": "bench", "direction": "h"},
    {"id": "bench_4", "x": 18, "y": 21, "type": "bench", "direction": "h"},
    # Campfire
    {"id": "campfire", "x": 13, "y": 15, "type": "campfire"},
] + _AUTO_TREES

# Agent presets — 5 villagers
AGENTS = [
    {
        "id": "a1",
        "name": "小梅",
        "role": "村民",
        "x": 8, "y": 8,
        "personality": {"O": 0.7, "C": 0.6, "E": 0.85, "A": 0.9, "N": 0.3},
        "color": "#ff6b6b",
        "backstory": "热心肠的年轻女孩，喜欢和人聊天，看到谁都打招呼。",
    },
    {
        "id": "a2",
        "name": "老王",
        "role": "工匠",
        "x": 25, "y": 7,
        "personality": {"O": 0.4, "C": 0.9, "E": 0.35, "A": 0.6, "N": 0.5},
        "color": "#4ecdc4",
        "backstory": "沉默寡言的中年木匠，做事认真但不太会聊天，喜欢在长椅上发呆。",
    },
    {
        "id": "a3",
        "name": "阿诗",
        "role": "吟游诗人",
        "x": 35, "y": 12,
        "personality": {"O": 0.95, "C": 0.2, "E": 0.8, "A": 0.7, "N": 0.6},
        "color": "#ffe66d",
        "backstory": "流浪诗人，脑子里全是故事和旋律，总是在篝火旁唱歌。",
    },
    {
        "id": "a4",
        "name": "小石头",
        "role": "学者",
        "x": 5, "y": 22,
        "personality": {"O": 0.85, "C": 0.7, "E": 0.25, "A": 0.5, "N": 0.7},
        "color": "#a29bfe",
        "backstory": "内向的书呆子，总在观察和思考，偶尔会说出惊人之语。",
    },
    {
        "id": "a5",
        "name": "集市张",
        "role": "商人",
        "x": 28, "y": 20,
        "personality": {"O": 0.5, "C": 0.8, "E": 0.9, "A": 0.4, "N": 0.4},
        "color": "#fd9644",
        "backstory": "精明的商人，喜欢讨价还价，最爱在集市上和人吹牛。",
    },
]
