/* ============================================================
   Pixel Town v4 — Storybook Aesthetic
   Soft watercolor tiles · cute rounded agents · fireflies
   ============================================================ */

// ============================================================
// 1. CONSTANTS
// ============================================================
const TILE = 24, COLS = 40, ROWS = 31;
const W = COLS * TILE, H = ROWS * TILE;

// ============================================================
// 2. STATE
// ============================================================
let worldMap = [], buildings = [], objects = [];
let agentStates = {};
let speechBubbles = [], particles = [], fireflies = [];
let paused = false, tickSpeed = 8, selectedAgentId = null;
let lastFrameTime = performance.now(), time = 0;
let eventLog = [], lastDetailAgent = null;
let charViewAgentId = null;  // which agent is selected in character view

// Day/night cycle state
let timeOfDay = 6.0, dayPhase = 'dawn', dayNumber = 1, timeLabel = '';

// Story threads: {key: {title, type, events[], lastUpdate}}
let storyThreads = {};

// Relationship snapshot for change detection
let relationSnapshots = {};

// Importance filter: 0=all, 2=chat+, 3=important+
let storyFilterLevel = 1;  // 1=show all interactions, 2=chat+, 3=important+
let ws = null;

// ============================================================
// ASSET IMAGES (user-provided art, procedural fallback)
// ============================================================
let mapImgLoaded = false, mapImgErrored = false;
const mapImg = new Image();
const charImg = {}; // id → Image, preloaded before render
let assetsReady = false;

function loadAssets() {
  mapImg.src = 'assets/map.png';
  mapImg.onload = () => { mapImgLoaded = true; };
  mapImg.onerror = () => { mapImgErrored = true; };
  const names = { a1: '小梅', a2: '老王', a3: '阿诗', a4: '小石头', a5: '集市张' };
  let loaded = 0;
  for (const [id, name] of Object.entries(names)) {
    const img = new Image();
    img.onload = () => { loaded++; if (loaded === 5) assetsReady = true; };
    img.onerror = () => { loaded++; if (loaded === 5) assetsReady = true; };
    img.src = `assets/char_${name}.png`;
    charImg[id] = img;
  }
  // Mark ready after 3s even if not all loaded
  setTimeout(() => { assetsReady = true; }, 3000);
}

// ============================================================
// 3. UTILITY
// ============================================================
function lerp(a, b, t) { return a + (b - a) * t; }
function lerpColor(c1, c2, t) {
  const r1 = parseInt(c1.slice(1,3),16), g1 = parseInt(c1.slice(3,5),16), b1 = parseInt(c1.slice(5,7),16);
  const r2 = parseInt(c2.slice(1,3),16), g2 = parseInt(c2.slice(3,5),16), b2 = parseInt(c2.slice(5,7),16);
  const r = Math.round(lerp(r1,r2,t)), g = Math.round(lerp(g1,g2,t)), b = Math.round(lerp(b1,b2,t));
  return `rgb(${r},${g},${b})`;
}

// Seeded random
let _seed = 42;
function seededRand() { _seed = (_seed * 16807) % 2147483647; return (_seed - 1) / 2147483646; }

// ============================================================
// 4. TILE PRERENDERING (soft watercolor style)
// ============================================================
const tileCache = {};

function prerenderTiles() {
  // 0: grass — soft green with subtle variation
  const grassCanvas = document.createElement('canvas'); grassCanvas.width = grassCanvas.height = TILE;
  const gc = grassCanvas.getContext('2d');
  gc.fillStyle = '#c8d6a0'; gc.fillRect(0,0,TILE,TILE);
  // subtle noise-like dots
  for (let i = 0; i < 15; i++) {
    const sx = Math.floor(seededRand()*TILE), sy = Math.floor(seededRand()*TILE);
    const shade = seededRand() > 0.5 ? '#bed298' : '#d2dea8';
    gc.fillStyle = shade; gc.fillRect(sx, sy, 2, 2);
  }
  // occasional tiny flower
  for (let i = 0; i < 2; i++) {
    if (seededRand() > 0.5) {
      const fx = 3 + Math.floor(seededRand()*18), fy = 3 + Math.floor(seededRand()*18);
      gc.fillStyle = ['#fff5e6','#ffe8cc','#f0d0f0','#ffffcc'][Math.floor(seededRand()*4)];
      gc.fillRect(fx, fy, 2, 2);
    }
  }
  tileCache[0] = grassCanvas;

  // 1: water — blue gradient with ripple lines
  const waterCanvas = document.createElement('canvas'); waterCanvas.width = waterCanvas.height = TILE;
  const wc = waterCanvas.getContext('2d');
  const wGrad = wc.createLinearGradient(0, 0, 0, TILE);
  wGrad.addColorStop(0, '#7eb8da'); wGrad.addColorStop(0.5, '#6badd1'); wGrad.addColorStop(1, '#5a9dc4');
  wc.fillStyle = wGrad; wc.fillRect(0,0,TILE,TILE);
  // ripple lines
  wc.strokeStyle = 'rgba(255,255,255,0.18)'; wc.lineWidth = 1;
  for (let ry = 4; ry < TILE; ry += 6) {
    wc.beginPath(); wc.moveTo(0, ry); wc.lineTo(TILE, ry - 2); wc.stroke();
  }
  tileCache[1] = waterCanvas;

  // 2: stone — warm gray with pebble texture
  const stoneCanvas = document.createElement('canvas'); stoneCanvas.width = stoneCanvas.height = TILE;
  const sc = stoneCanvas.getContext('2d');
  sc.fillStyle = '#c8c0b4'; sc.fillRect(0,0,TILE,TILE);
  for (let i = 0; i < 12; i++) {
    const sx = Math.floor(seededRand()*TILE), sy = Math.floor(seededRand()*TILE);
    sc.fillStyle = seededRand() > 0.5 ? '#d4ccc0' : '#bcb4a8';
    sc.fillRect(sx, sy, seededRand() > 0.6 ? 3 : 2, seededRand() > 0.6 ? 3 : 2);
  }
  tileCache[2] = stoneCanvas;

  // 3: flowers — grass base + colorful flower dots
  const flowerCanvas = document.createElement('canvas'); flowerCanvas.width = flowerCanvas.height = TILE;
  const fc = flowerCanvas.getContext('2d');
  fc.fillStyle = '#a8c888'; fc.fillRect(0,0,TILE,TILE);
  const flowerColors = ['#ff9eb5','#ffe88c','#ffffff','#ffb878','#d8a0e8','#ffccd5'];
  for (let i = 0; i < 7; i++) {
    const fx = 2 + Math.floor(seededRand()*20), fy = 2 + Math.floor(seededRand()*20);
    fc.fillStyle = flowerColors[Math.floor(seededRand()*flowerColors.length)];
    fc.fillRect(fx, fy, 2, 2);
    fc.fillRect(fx+1, fy-1, 1, 1);
    fc.fillRect(fx-1, fy+1, 1, 1);
  }
  tileCache[3] = flowerCanvas;

  // 4: bridge — wooden planks
  const bridgeCanvas = document.createElement('canvas'); bridgeCanvas.width = bridgeCanvas.height = TILE;
  const bc = bridgeCanvas.getContext('2d');
  bc.fillStyle = '#c8b898'; bc.fillRect(0,0,TILE,TILE);
  for (let py = 0; py < TILE; py += 6) {
    bc.fillStyle = '#b09870'; bc.fillRect(0, py, TILE, 4);
    bc.fillStyle = '#c8b080'; bc.fillRect(0, py + 1, TILE, 2);
    // nail dots
    bc.fillStyle = '#8a6a4a'; bc.fillRect(3, py + 1, 2, 2); bc.fillRect(TILE - 5, py + 1, 2, 2);
  }
  // vertical grain lines
  bc.strokeStyle = 'rgba(0,0,0,0.04)'; bc.lineWidth = 1;
  for (let vx = 4; vx < TILE; vx += 6) { bc.beginPath(); bc.moveTo(vx, 0); bc.lineTo(vx, TILE); bc.stroke(); }
  tileCache[4] = bridgeCanvas;
}

// ============================================================
// 5. CANVAS RENDERER
// ============================================================
const canvas = document.getElementById('c');
canvas.width = W; canvas.height = H;
const ctx = canvas.getContext('2d');

// ---- Buildings ----
function drawBuilding(b) {
  const bx = b.x * TILE, by = b.y * TILE, bw = b.w * TILE, bh = b.h * TILE;
  const wc = b.color || '#f0d8b0', rc = b.roof || '#d4956b';
  const isWell = b.id === 'well';
  const isMarket = b.id === 'market';

  if (isWell) {
    // Circular well
    const cx = bx + bw/2, cy = by + bh/2;
    ctx.fillStyle = '#c8b898'; ctx.beginPath(); ctx.arc(cx, cy, 10, 0, Math.PI*2); ctx.fill();
    ctx.strokeStyle = '#a09078'; ctx.lineWidth = 2; ctx.stroke();
    ctx.fillStyle = '#6a8090'; ctx.beginPath(); ctx.arc(cx, cy, 7, 0, Math.PI*2); ctx.fill();
    // wooden beam
    ctx.fillStyle = '#8b6914'; ctx.fillRect(cx - 12, cy - 2, 24, 4);
    ctx.fillRect(cx - 1, cy - 16, 2, 14);
    // bucket
    const bucketY = cy - 14 + Math.sin(time * 0.003) * 2;
    ctx.fillStyle = '#a08060'; ctx.fillRect(cx - 4, bucketY, 8, 6);
    return;
  }

  // Shadow
  ctx.fillStyle = 'rgba(0,0,0,0.08)'; ctx.fillRect(bx + 3, by + TILE/2 + 3, bw, bh - TILE/2);
  // Wall
  ctx.fillStyle = wc; ctx.fillRect(bx, by + TILE/2, bw, bh - TILE/2 + 2);
  // Subtle wall texture
  ctx.fillStyle = 'rgba(0,0,0,0.03)';
  for (let ly = by + TILE/2 + 4; ly < by + bh; ly += 8) ctx.fillRect(bx + 2, ly, bw - 4, 1);

  // Roof
  const roofOverhang = 5, roofPeak = 8;
  ctx.fillStyle = rc;
  ctx.beginPath();
  ctx.moveTo(bx - roofOverhang, by + TILE/2);
  ctx.lineTo(bx + bw/2, by - roofPeak);
  ctx.lineTo(bx + bw + roofOverhang, by + TILE/2);
  ctx.closePath(); ctx.fill();
  // Roof highlight
  ctx.fillStyle = 'rgba(255,255,255,0.12)';
  ctx.beginPath();
  ctx.moveTo(bx + 2, by + TILE/2);
  ctx.lineTo(bx + bw/2, by - roofPeak + 2);
  ctx.lineTo(bx + bw/2 + 4, by + TILE/2);
  ctx.closePath(); ctx.fill();

  if (isMarket) {
    // Awning stripes
    const awningColors = ['#f0d0d0','#fff','#f0d0d0','#fff','#f0d0d0','#fff'];
    for (let ax = bx + 2; ax < bx + bw - 2; ax += 5) {
      ctx.fillStyle = awningColors[Math.floor((ax - bx) / 5) % awningColors.length];
      ctx.fillRect(ax, by + TILE/2 - 3, 5, bh - TILE/2 + 6);
    }
    // Goods on display
    const goods = ['#ff6b6b','#ffe66d','#a29bfe','#4ecdc4'];
    goods.forEach((cl, i) => {
      ctx.fillStyle = cl; ctx.fillRect(bx + 10 + i * 16, by + bh - 12, 8, 8);
    });
  } else {
    // Windows with warm glow
    const wCount = bw > TILE * 2 ? 2 : 1;
    for (let wi = 0; wi < wCount; wi++) {
      const wx = bx + bw/(wCount+1) * (wi+1) - 5;
      ctx.fillStyle = '#ffe8a0'; ctx.fillRect(wx, by + TILE/2 + 6, 10, 10);
      ctx.fillStyle = 'rgba(255,230,140,0.35)'; ctx.fillRect(wx - 2, by + TILE/2 + 4, 14, 14);
      // window cross
      ctx.fillStyle = 'rgba(0,0,0,0.15)';
      ctx.fillRect(wx + 4, by + TILE/2 + 6, 2, 10);
      ctx.fillRect(wx, by + TILE/2 + 10, 10, 2);
    }
  }
}

// ---- Objects ----
function drawObject(obj) {
  const ox = obj.x * TILE, oy = obj.y * TILE;

  if (obj.type === 'bench') {
    // Wooden bench
    ctx.fillStyle = '#8b6914';
    ctx.fillRect(ox + 3, oy + 16, 18, 5); // seat
    ctx.fillStyle = '#a07820';
    ctx.fillRect(ox + 4, oy + 21, 4, 4); ctx.fillRect(ox + 16, oy + 21, 4, 4); // legs
    ctx.fillStyle = '#7a5a10'; ctx.fillRect(ox + 2, oy + 15, 20, 2); // top slat
  } else if (obj.type === 'campfire') {
    // Glowing fire
    const flicker = Math.sin(time * 0.012) * 2;
    // glow halo
    const glow = ctx.createRadialGradient(ox + 12, oy + 16, 4, ox + 12, oy + 16, 18);
    glow.addColorStop(0, 'rgba(255,160,60,0.35)'); glow.addColorStop(1, 'rgba(255,160,60,0)');
    ctx.fillStyle = glow; ctx.fillRect(ox - 8, oy - 2, 40, 40);
    // wood
    ctx.fillStyle = '#5a3a1a'; ctx.fillRect(ox + 4, oy + 18, 16, 4);
    // fire layers
    ['#ff4500','#ff6a30','#ff9a50','#ffcc30'].forEach((cl, i) => {
      ctx.fillStyle = cl;
      const fy = oy + 14 - i * 3 + (i % 2 ? flicker : -flicker) * 0.4;
      const fr = 4 + i * 1.2;
      ctx.beginPath(); ctx.arc(ox + 12, fy, fr, 0, Math.PI*2); ctx.fill();
    });
    // sparks
    if (Math.random() < 0.5) {
      particles.push({
        x: ox + 8 + Math.random()*8, y: oy + 4,
        vx: (Math.random()-0.5)*0.6, vy: -(Math.random()*1.8+0.8),
        life: 15 + Math.random()*20, color: Math.random() > 0.5 ? '#ffcc30' : '#ff6a30',
      });
    }
  } else if (obj.type === 'tree') {
    drawTree(ox, oy);
  }
}

function drawTree(ox, oy) {
  // Trunk
  ctx.fillStyle = '#9b6b3a'; ctx.fillRect(ox + 9, oy + 13, 6, 11);
  ctx.fillStyle = '#b8844a'; ctx.fillRect(ox + 10, oy + 13, 3, 11); // highlight
  // Canopy layers (soft overlapping circles)
  const canopyColor = '#7bb860', canopyDark = '#5e9446', canopyLight = '#90cc78';
  const layers = [
    { x: 12, y: 6, r: 12, c: canopyDark },
    { x: 5, y: 3, r: 9, c: canopyColor },
    { x: 19, y: 4, r: 9, c: canopyColor },
    { x: 12, y: -1, r: 8, c: canopyLight },
    { x: 8, y: 8, r: 7, c: canopyLight },
  ];
  layers.forEach(l => {
    ctx.fillStyle = l.c;
    ctx.beginPath(); ctx.arc(ox + l.x, oy + l.y, l.r, 0, Math.PI*2); ctx.fill();
  });
}

// ---- Agent ----
function drawAgent(a, x, y) {
  const cx = x + 12, cy = y + 10; // center of sprite
  const c = a.color || '#aaa';
  const bounce = Math.sin(time * 0.005 + (a.id || 'a').charCodeAt(0)) * 0.4;
  const breath = 1 + Math.sin(time * 0.004 + a.id.charCodeAt(1)) * 0.03;

  ctx.save();
  ctx.translate(x + 12, y + 18);
  ctx.scale(breath, breath);

  // Shadow
  ctx.fillStyle = 'rgba(0,0,0,0.12)';
  ctx.beginPath(); ctx.ellipse(0, 6, 8, 2, 0, 0, Math.PI*2); ctx.fill();

  // Legs (short rounded)
  ctx.fillStyle = darkenColor(c, 0.5);
  roundRect(ctx, -5, 1, 4, 5, 2); roundRect(ctx, 1, 1, 4, 5, 2);

  // Body (rounded rectangle)
  ctx.fillStyle = c;
  roundRect(ctx, -6, -5, 12, 9, 4);
  // Body highlight
  ctx.fillStyle = 'rgba(255,255,255,0.15)'; roundRect(ctx, -4, -4, 5, 4, 2);

  // Arms
  ctx.fillStyle = darkenColor(c, 0.3);
  roundRect(ctx, -8, -4, 2.5, 6, 1.5); roundRect(ctx, 5.5, -4, 2.5, 6, 1.5);

  // Head
  ctx.fillStyle = '#f4c7a8'; roundRect(ctx, -5, -13, 10, 9, 5);
  // Hair
  ctx.fillStyle = darkenColor(c, 0.55);
  roundRect(ctx, -6, -15, 12, 4, 3);
  ctx.fillRect(ctx, -6, -13, 3, 5); ctx.fillRect(ctx, 3, -13, 3, 5);
  // Eyes
  ctx.fillStyle = '#1a1a1a';
  ctx.fillRect(ctx, -3, -10, 2, 2.5); ctx.fillRect(ctx, 1, -10, 2, 2.5);

  ctx.restore();

  // Selection ring
  if (a.id === selectedAgentId) {
    const pulse = Math.sin(time * 0.005) * 0.3 + 0.7;
    ctx.strokeStyle = `rgba(90,158,111,${pulse})`; ctx.lineWidth = 2.5;
    ctx.setLineDash([4, 3]); ctx.lineDashOffset = time * 0.02;
    ctx.beginPath(); ctx.roundRect(x - 4, y - 4, TILE + 8, TILE + 10, 8); ctx.stroke();
    ctx.setLineDash([]);
  }
}

// ---- Large fallback agent (while sprite loads) ----
function drawAgentLargeFallback(a, x, y) {
  const c = a.color || '#aaa';
  const bob = Math.sin(time * 0.004 + (a.id || 'a').charCodeAt(1)) * 1.5;
  // Ground shadow
  ctx.fillStyle = 'rgba(0,0,0,0.2)';
  ctx.beginPath(); ctx.ellipse(x + TILE/2, y + TILE + 1, 18, 3, 0, 0, Math.PI * 2); ctx.fill();
  // Body (colored rounded rect, ~120px tall)
  ctx.fillStyle = c;
  ctx.beginPath(); roundRectPath(ctx, x + 4, y - 90 + bob, 16, 80, 8); ctx.fill();
  // Head (skin tone circle)
  ctx.fillStyle = '#f4c7a8';
  ctx.beginPath(); ctx.arc(x + 12, y - 94 + bob, 10, 0, Math.PI * 2); ctx.fill();
  // Hair
  ctx.fillStyle = darkenColor(c, 0.55);
  ctx.beginPath(); ctx.arc(x + 12, y - 100 + bob, 11, Math.PI, Math.PI * 2); ctx.fill();
  // Eyes
  ctx.fillStyle = '#1a1a1a';
  ctx.fillRect(x + 8, y - 97 + bob, 2, 2); ctx.fillRect(x + 14, y - 97 + bob, 2, 2);
}

// ---- Agent from sprite ----
const SPRITE_H = 128; // display height for character sprites
function drawAgentFromSprite(img, a, x, y) {
  const scale = SPRITE_H / img.naturalHeight;
  const w = img.naturalWidth * scale;
  const h = SPRITE_H;
  const dx = x + TILE/2 - w/2;
  const dy = y + TILE - h + 2; // feet at tile bottom

  // Ground shadow — anchors character to the map
  ctx.fillStyle = 'rgba(0,0,0,0.2)';
  ctx.beginPath(); ctx.ellipse(x + TILE/2, y + TILE + 1, w * 0.42, 3, 0, 0, Math.PI * 2); ctx.fill();
  ctx.fillStyle = 'rgba(0,0,0,0.08)';
  ctx.beginPath(); ctx.ellipse(x + TILE/2, y + TILE + 1, w * 0.55, 4, 0, 0, Math.PI * 2); ctx.fill();

  // Gentle bob animation
  const bob = Math.sin(time * 0.003 + (a.id || 'a').charCodeAt(1)) * 1.5;
  ctx.drawImage(img, dx, dy + bob, w, h);

  // Selection ring
  if (a.id === selectedAgentId) {
    const pulse = Math.sin(time * 0.004) * 0.25 + 0.75;
    ctx.strokeStyle = `rgba(90,158,111,${pulse})`;
    ctx.lineWidth = 3;
    ctx.shadowColor = 'rgba(90,158,111,0.5)';
    ctx.shadowBlur = 10;
    ctx.setLineDash([5, 4]); ctx.lineDashOffset = time * 0.02;
    ctx.beginPath();
    ctx.roundRect(dx - 4, dy - 4, w + 8, h + 8, 10);
    ctx.stroke();
    ctx.setLineDash([]);
    ctx.shadowColor = 'transparent'; ctx.shadowBlur = 0;
  }
}

// ---- Emoji ----
function drawEmoji(a, x, y, spriteMode) {
  const emoji = a.emoji || '\u{1F636}';
  ctx.font = '18px sans-serif'; ctx.textAlign = 'center';
  const float = Math.sin(time * 0.004 + (a.id || 'a').charCodeAt(0)) * 2.5;
  const emY = spriteMode ? y + TILE - SPRITE_H - 4 : y - 8;
  ctx.fillText(emoji, x + 12, emY + float);
  ctx.textAlign = 'start';
}

// ---- Speech bubble ----
function drawSpeechBubbles() {
  for (let i = speechBubbles.length - 1; i >= 0; i--) {
    const sb = speechBubbles[i]; sb.life--;
    if (sb.life <= 0) { speechBubbles.splice(i, 1); continue; }
    const a = agentStates[sb.agentId];
    if (!a) continue;
    sb.x = a.displayX;
    // Position above character: higher for tall sprites
    const img = charImg[a.id];
    const isSprite = img && img.complete && img.naturalWidth > 0;
    const bubbleTop = isSprite ? a.displayY + TILE - SPRITE_H - 30 : a.displayY - 24;
    sb.y = bubbleTop;

    const alpha = Math.min(1, sb.life / 35);
    ctx.font = 'bold 13px "Noto Sans SC"';
    const tw = ctx.measureText(sb.text).width + 24;
    const bw = Math.max(tw, 56);
    const bx = sb.x + TILE/2 - bw/2, by = sb.y;

    // Bubble background with shadow
    ctx.shadowColor = 'rgba(0,0,0,0.12)'; ctx.shadowBlur = 8; ctx.shadowOffsetY = 3;
    ctx.fillStyle = `rgba(255,255,255,${alpha * 0.97})`;
    ctx.beginPath(); roundRectPath(ctx, bx, by, bw, 28, 14); ctx.fill();
    ctx.shadowColor = 'transparent'; ctx.shadowBlur = 0; ctx.shadowOffsetY = 0;
    ctx.strokeStyle = `rgba(0,0,0,${alpha * 0.14})`; ctx.lineWidth = 1.5;
    ctx.beginPath(); roundRectPath(ctx, bx, by, bw, 28, 14); ctx.stroke();
    // Pointer pointing down toward character
    ctx.fillStyle = `rgba(255,255,255,${alpha * 0.97})`;
    ctx.beginPath(); ctx.moveTo(sb.x + TILE/2 - 6, by + 28); ctx.lineTo(sb.x + TILE/2, by + 37); ctx.lineTo(sb.x + TILE/2 + 6, by + 28);
    ctx.closePath(); ctx.fill(); ctx.stroke();
    // Text
    ctx.fillStyle = `rgba(30,30,36,${alpha})`;
    ctx.textAlign = 'center'; ctx.fillText(sb.text, sb.x + TILE/2, by + 19); ctx.textAlign = 'start';
  }
}

// ---- Fireflies ----
function updateFireflies() {
  for (const ff of fireflies) {
    ff.x += ff.vx + Math.sin(time * 0.003 + ff.phase) * 0.3;
    ff.y += ff.vy + Math.cos(time * 0.004 + ff.phase) * 0.3;
    // Wrap around
    if (ff.x < -20) ff.x = W + 20;
    if (ff.x > W + 20) ff.x = -20;
    if (ff.y < -20) ff.y = H + 20;
    if (ff.y > H + 20) ff.y = -20;
    // Glow pulse
    ff.glow = 0.3 + Math.sin(time * 0.006 + ff.phase) * 0.3 + Math.sin(time * 0.013 + ff.phase * 1.7) * 0.2;
  }
}

function drawFireflies() {
  for (const ff of fireflies) {
    const alpha = Math.max(0, ff.glow);
    // Outer glow
    const glow = ctx.createRadialGradient(ff.x, ff.y, 0, ff.x, ff.y, ff.r * 3);
    glow.addColorStop(0, `rgba(220,255,180,${alpha * 0.5})`);
    glow.addColorStop(1, 'rgba(220,255,180,0)');
    ctx.fillStyle = glow; ctx.fillRect(ff.x - ff.r*3, ff.y - ff.r*3, ff.r*6, ff.r*6);
    // Core dot
    ctx.fillStyle = `rgba(240,255,200,${alpha})`;
    ctx.beginPath(); ctx.arc(ff.x, ff.y, ff.r, 0, Math.PI*2); ctx.fill();
  }
}

// ---- Particles ----
function updateParticles() {
  for (let i = particles.length - 1; i >= 0; i--) {
    const p = particles[i]; p.x += p.vx; p.y += p.vy; p.life--;
    if (p.life <= 0) particles.splice(i, 1);
  }
}

function drawParticles() {
  for (const p of particles) {
    ctx.globalAlpha = p.life / 30;
    ctx.fillStyle = p.color;
    ctx.beginPath(); ctx.arc(p.x, p.y, 1.2, 0, Math.PI*2); ctx.fill();
  }
  ctx.globalAlpha = 1;
}

// ---- Main Render Loop ----
function mainRender(now) {
  requestAnimationFrame(mainRender);
  const dt = Math.min((now - lastFrameTime) / 1000, 0.1);
  lastFrameTime = now;
  time = now;

  // Background: user-drawn map, scaled to canvas (aligns with tile grid)
  if (mapImgLoaded && mapImg.naturalWidth > 0) {
    ctx.drawImage(mapImg, 0, 0, W, H);
  } else {
    const sky = ctx.createLinearGradient(0, 0, 0, H);
    sky.addColorStop(0, '#d4e8f0'); sky.addColorStop(0.5, '#dce8d0'); sky.addColorStop(1, '#c8d4b8');
    ctx.fillStyle = sky; ctx.fillRect(0, 0, W, H);
    for (let row = 0; row < ROWS; row++)
      for (let col = 0; col < COLS; col++) {
        const t = (worldMap[row] && worldMap[row][col] !== undefined) ? worldMap[row][col] : 0;
        const tile = tileCache[t];
        if (tile) ctx.drawImage(tile, col * TILE, row * TILE);
      }
    for (const b of buildings) drawBuilding(b);
    for (const o of objects) drawObject(o);
  }

  // Fireflies (behind agents)
  updateFireflies();
  drawFireflies();

  // Agents (sort by Y for depth)
  const sorted = Object.values(agentStates).sort((a, b) => (a.displayY || 0) - (b.displayY || 0));
  for (const a of sorted) {
    if (a.targetX !== undefined) a.displayX = lerp(a.displayX, a.targetX, Math.min(1, dt * 9));
    if (a.targetY !== undefined) a.displayY = lerp(a.displayY, a.targetY, Math.min(1, dt * 9));
    a.displayX = Math.max(0, Math.min(W - TILE, a.displayX));
    a.displayY = Math.max(SPRITE_H, Math.min(H - TILE, a.displayY));

    const img = charImg[a.id];
    if (img && img.complete && img.naturalWidth > 0) {
      drawAgentFromSprite(img, a, a.displayX, a.displayY);
    } else {
      drawAgentLargeFallback(a, a.displayX, a.displayY);
    }
  }
}

// ---- Drawing helpers ----
function roundRect(ctx, x, y, w, h, r) {
  ctx.beginPath(); roundRectPath(ctx, x, y, w, h, r); ctx.fill();
}
function roundRectPath(ctx, x, y, w, h, r) {
  ctx.beginPath();
  ctx.moveTo(x + r, y); ctx.lineTo(x + w - r, y);
  ctx.arcTo(x + w, y, x + w, y + r, r);
  ctx.lineTo(x + w, y + h - r); ctx.arcTo(x + w, y + h, x + w - r, y + h, r);
  ctx.lineTo(x + r, y + h); ctx.arcTo(x, y + h, x, y + h - r, r);
  ctx.lineTo(x, y + r); ctx.arcTo(x, y, x + r, y, r);
  ctx.closePath();
}
function darkenColor(hex, amt) {
  let r = parseInt(hex.slice(1,3),16), g = parseInt(hex.slice(3,5),16), b = parseInt(hex.slice(5,7),16);
  r = Math.floor(r * (1 - amt)); g = Math.floor(g * (1 - amt)); b = Math.floor(b * (1 - amt));
  return `rgb(${r},${g},${b})`;
}

// ============================================================
// 6. CLICK HANDLER (distance-based)
// ============================================================
function getClickTarget(mx, my) {
  let bestId = null, bestDist = Infinity;
  for (const [id, a] of Object.entries(agentStates)) {
    const img = charImg[id];
    const useImg = img && img.complete && img.naturalWidth > 0;
    // Center: sprite is feet-anchored at tile bottom, extends upward SPRITE_H px
    const cx = a.displayX + TILE/2;
    const cy = useImg ? a.displayY + TILE - SPRITE_H * 0.45 : a.displayY + 10;
    const radius = useImg ? Math.max(SPRITE_H * 0.35, 35) : 24;
    const dist = Math.hypot(mx - cx, my - cy);
    if (dist < bestDist && dist < radius) { bestDist = dist; bestId = id; }
  }
  return bestId;
}

canvas.addEventListener('click', (e) => {
  const rect = canvas.getBoundingClientRect();
  const sx = W / rect.width, sy = H / rect.height;
  const mx = (e.clientX - rect.left) * sx, my = (e.clientY - rect.top) * sy;
  const tid = getClickTarget(mx, my);
  if (tid) {
    ws.send(JSON.stringify({ type: 'click_agent', agent_id: tid }));
    document.querySelector('#tabs button[data-tab="tab-character"]').click();
  }
});

// ============================================================
// 7. WEBSOCKET
// ============================================================
function connectWS() {
  const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
  ws = new WebSocket(`${proto}//${location.host}/ws`);

  ws.onmessage = (e) => {
    const msg = JSON.parse(e.data);
    switch (msg.type) {
      case 'world_init':
        worldMap = msg.map; buildings = msg.buildings; objects = msg.objects;
        paused = msg.paused; tickSpeed = msg.tick_speed;
        timeOfDay = msg.time_of_day || 6; dayPhase = msg.day_phase || 'dawn';
        dayNumber = msg.day_number || 1; timeLabel = msg.time_label || '';
        for (const a of msg.agents) {
          agentStates[a.id] = {
            ...a,
            displayX: a.x * TILE, displayY: a.y * TILE,
            targetX: a.x * TILE, targetY: a.y * TILE,
            emoji: a.emotion?.emoji || '\u{1F636}',
            emotion: a.emotion, needs: a.needs,
            relationships: a.relationships, gossip: a.gossip_heard,
          };
          // Save initial relationship snapshot
          relationSnapshots[a.id] = {};
          for (const [rid, r] of Object.entries(a.relationships || {})) {
            relationSnapshots[a.id][rid] = { affinity: r.affinity, stage: r.stage || 'stranger' };
          }
        }
        updateSpeedUI(); updatePauseUI();
        updateTimeDisplay();
        break;

      case 'agent_update':
        if (agentStates[msg.agent_id]) {
          const a = agentStates[msg.agent_id];
          a.targetX = msg.x * TILE; a.targetY = msg.y * TILE;
          a.x = msg.x; a.y = msg.y;
          if (msg.emoji) a.emoji = msg.emoji;
          if (msg.emotion) a.emotion = msg.emotion;
          if (msg.needs) a.needs = msg.needs;
        }
        break;

      case 'speech':
      case 'interaction':
      case 'gossip':
        console.log('[WS] ' + msg.type + ' from ' + msg.agent_name + ' imp=' + msg.importance + ' txt=' + (msg.text||'').substring(0,30));
        if (agentStates[msg.agent_id]) {
          const a = agentStates[msg.agent_id];
          a.emoji = msg.emoji || a.emoji; a.emotion = msg.emotion || a.emotion;
          if (msg.text) {
            speechBubbles.push({ agentId: msg.agent_id, text: msg.text, x: a.displayX, y: a.displayY - 120, life: 200 });
          }
          for (let i = 0; i < (msg.text ? 5 : 3); i++) {
            particles.push({ x: a.displayX + Math.random()*24, y: a.displayY, vx: (Math.random()-0.5)*1.5, vy: -(Math.random()*2.5+1), life: 22+Math.random()*22, color: '#fff' });
          }
          // Track time & story
          if (msg.time_of_day !== undefined) { timeOfDay = msg.time_of_day; dayPhase = msg.day_phase; dayNumber = msg.day_number; timeLabel = msg.time_label; }
          updateTimeDisplay();
          addStoryEvent(msg);
        }
        break;

      case 'agent_idle':
        if (agentStates[msg.agent_id]) {
          const a = agentStates[msg.agent_id];
          if (msg.emoji) a.emoji = msg.emoji;
          if (msg.emotion) a.emotion = msg.emotion;
          if (msg.needs) a.needs = msg.needs;
          if (msg.time_of_day !== undefined) { timeOfDay = msg.time_of_day; dayPhase = msg.day_phase; dayNumber = msg.day_number; timeLabel = msg.time_label; }
          updateTimeDisplay();
        }
        break;

      case 'agent_detail':
        lastDetailAgent = msg.agent;
        selectedAgentId = msg.agent.id;
        showCharacterView(msg.agent.id);
        break;

      case 'pause_state': paused = msg.paused; updatePauseUI(); break;
      case 'speed_changed': tickSpeed = msg.speed; updateSpeedUI(); break;
    }
  };

  ws.onclose = () => { console.log('WebSocket disconnected, reconnecting...'); setTimeout(connectWS, 3000); };
  ws.onerror = () => {};
}

// ============================================================
// 8. UI COMPONENTS
// ============================================================

// ── Time display ──
function updateTimeDisplay() {
  const el = document.getElementById('time-display');
  if (el) {
    const icons = {dawn:'🌅', day:'☀️', dusk:'🌆', night:'🌙'};
    const h = Math.floor(timeOfDay), m = Math.floor((timeOfDay-h)*60);
    el.innerHTML = `${icons[dayPhase]||''} 第${dayNumber}天 ${String(h).padStart(2,'0')}:${String(m).padStart(2,'0')}`;
  }
  // Update night overlay
  const overlay = document.getElementById('night-overlay');
  if (overlay) {
    const phase = dayPhase;
    if (phase === 'night') {
      overlay.style.background = 'rgba(10,15,40,0.45)';
    } else if (phase === 'dusk') {
      overlay.style.background = 'rgba(180,100,50,0.2)';
    } else if (phase === 'dawn') {
      overlay.style.background = 'rgba(200,150,100,0.12)';
    } else {
      overlay.style.background = 'transparent';
    }
  }
}

// ── Story Event System ──
const IMPORTANCE_LABELS = {0:'', 1:'', 2:'💬', 3:'★★★', 4:'★★★★', 5:'★★★★★'};
const IMPORTANCE_CLASS = {0:'imp-0', 1:'imp-1', 2:'imp-chat', 3:'imp-important', 4:'imp-major', 5:'imp-milestone'};

function addStoryEvent(msg) {
  const imp = msg.importance || 0;
  console.log('[story] type=' + msg.type + ' imp=' + imp + ' who=' + (msg.agent_name || msg.name) + ' txt=' + (msg.text||'').substring(0,30));
  if (imp === 0) return; // skip movement/idle

  const entry = {
    type: msg.type,
    who: msg.agent_name || msg.name,
    agentId: msg.agent_id,
    text: msg.text || msg.target || '',
    target: msg.target || '',
    gossipAbout: msg.gossip_about || '',
    importance: imp,
    color: msg.color || '#5b9bd5',
    phase: msg.day_phase || dayPhase,
    timeLabel: msg.time_label || timeLabel,
    ts: Date.now(),
  };

  eventLog.unshift(entry);
  if (eventLog.length > 200) eventLog.length = 150;

  // Track story threads
  if (imp >= 2) trackStoryThread(entry);

  // Update relation snapshots
  if (msg.agent_id && agentStates[msg.agent_id]) {
    const a = agentStates[msg.agent_id];
    const rels = a.relationships || {};
    for (const [rid, r] of Object.entries(rels)) {
      if (!relationSnapshots[msg.agent_id]) relationSnapshots[msg.agent_id] = {};
      relationSnapshots[msg.agent_id][rid] = { affinity: r.affinity, stage: r.stage || 'stranger' };
    }
  }

  renderStoryFeed();
  if (charViewAgentId) showCharacterView(charViewAgentId);
}

function trackStoryThread(entry) {
  // Generate thread key from agent + target or gossip_about
  let key = null, title = '', type = 'chat';
  if (entry.gossipAbout && entry.target) {
    key = `${entry.agentId}_${entry.gossipAbout}_gossip`;
    title = `${entry.who} 🗣 ${entry.gossipAbout}`;
    type = 'gossip';
  } else if (entry.target && entry.agentId) {
    const ids = [entry.agentId, entry.target].sort();
    key = `${ids[0]}_${ids[1]}_chat`;
    title = `${entry.who} ↔ ${entry.target}`;
    type = 'chat';
  }
  if (!key) return;

  if (!storyThreads[key]) {
    storyThreads[key] = { title, type, events: [], lastUpdate: 0 };
  }
  storyThreads[key].events.push(entry);
  if (storyThreads[key].events.length > 20) storyThreads[key].events = storyThreads[key].events.slice(-20);
  storyThreads[key].lastUpdate = Date.now();
}

function renderStoryFeed() {
  const el = document.getElementById('story-feed');
  if (!el) return;

  const filtered = eventLog.filter(e => e.importance >= storyFilterLevel);
  const visible = filtered.slice(0, 30);

  // Group by day phase
  let currentPhase = '';
  let html = '';

  for (const e of visible) {
    if (e.phase !== currentPhase) {
      currentPhase = e.phase;
      const icons = {dawn:'🌅 黎明', day:'☀️ 白天', dusk:'🌆 黄昏', night:'🌙 夜晚'};
      html += `<div class="phase-divider">${icons[currentPhase]||currentPhase}</div>`;
    }
    const stars = IMPORTANCE_LABELS[e.importance] || '';
    const cls = IMPORTANCE_CLASS[e.importance] || '';
    const icon = e.type === 'speech' ? (e.gossipAbout ? '🗣' : '💬') : e.type === 'interaction' ? '📍' : '';
    html += `<div class="story-entry ${cls}">
      <span class="story-stars">${stars}</span>
      <span class="story-icon">${icon}</span>
      <b style="color:${e.color}">${e.who}</b>
      <span class="story-text">${e.text}</span>
      ${e.target && e.target !== e.who ? `<span class="story-arrow">→</span><span class="story-target">${e.target}</span>` : ''}
    </div>`;
  }

  if (filtered.length === 0) {
    html = '<div class="placeholder-text">等待故事发生...</div>';
  }

  el.innerHTML = html;
}

// ── Character View ──
function showCharacterView(agentId) {
  charViewAgentId = agentId;
  const a = agentStates[agentId];
  if (!a) return;

  const el = document.getElementById('char-view');
  if (!el) return;

  // Highlight selected char button
  document.querySelectorAll('.char-btn').forEach(b => b.classList.remove('active'));
  const btn = document.querySelector(`.char-btn[data-aid="${agentId}"]`);
  if (btn) btn.classList.add('active');

  // Story thread
  const charEvents = eventLog.filter(e => e.agentId === agentId || e.target === a.name || e.gossipAbout === a.name);
  const storyHtml = charEvents.slice(0, 8).map(e => {
    const icon = e.gossipAbout ? '🗣' : e.type === 'speech' ? '💬' : '📍';
    return `<div class="char-story-line">${icon} ${e.text}</div>`;
  }).join('') || '<div class="placeholder-text">还没发生什么...</div>';

  // Mood vector
  const mv = a.mood_vector || {};
  const moodBars = ['happiness','sadness','anxiety','anger','loneliness'].map(dim => {
    const v = mv[dim] || 0;
    const labels = {happiness:'愉悦', sadness:'悲伤', anxiety:'焦虑', anger:'愤怒', loneliness:'孤独'};
    const colors = {happiness:'#ffd700', sadness:'#5b9bd5', anxiety:'#e09860', anger:'#e07070', loneliness:'#8892a0'};
    return `<div class="mood-bar-row"><span class="mood-label">${labels[dim]}</span>
      <div class="mood-bar-wrap"><div class="mood-bar" style="width:${v*10}%;background:${colors[dim]}"></div></div>
      <span class="mood-val">${Math.round(v)}</span></div>`;
  }).join('');

  // Goal
  const goal = a.goal_progress;
  const goalHtml = goal ? `<div class="char-goal">🎯 ${goal.label}: ${goal.description} (${Math.round(goal.progress/goal.max_progress*100)}%)</div>` : '';

  // Open loops
  const loops = a.open_loops || [];
  const loopsHtml = loops.length ? loops.map(l => `<div class="char-loop">⚡ ${l}</div>`).join('') : '';

  // Beliefs
  const beliefs = a.beliefs || {};
  const beliefHtml = Object.entries(beliefs).map(([bid, b]) => {
    const otherName = Object.values(agentStates).find(x => x.id === bid)?.name || bid;
    return `<div class="char-belief"><span class="belief-name">${otherName}</span>: ${b.summary||''}</div>`;
  }).join('');

  // Agent header
  const emoji = a.emotion?.emoji || a.emoji || '\u{1F636}';
  const emotionText = a.emotion ? `${a.emotion.type} (${a.emotion.intensity?.toFixed(1)}/10)` : '';
  const needs = a.needs || {};
  const needDefs = [
    { k: 'hunger', i: '🍎', c: '#e09860' }, { k: 'social', i: '💬', c: '#5b9bd5' },
    { k: 'rest', i: '💤', c: '#5a9e6f' }, { k: 'purpose', i: '⭐', c: '#c8963e' },
  ];
  const needsHtml = needDefs.map(n => {
    const v = needs[n.k] || 50;
    return `<div class="need-row"><span class="need-icon">${n.i}</span>
      <div class="need-bar-wrap"><div class="need-bar" style="width:${v}%;background:${n.c}"></div></div>
      <span class="need-val">${Math.round(v)}</span></div>`;
  }).join('');

  el.innerHTML = `
    <div class="char-header">
      <span class="char-emoji">${emoji}</span>
      <div>
        <div class="char-name" style="color:${a.color}">${a.name}</div>
        <div class="char-role">${a.role||''}</div>
        <div class="char-emotion-text">${emotionText}</div>
      </div>
    </div>
    ${a.backstory ? `<div class="char-backstory">${a.backstory}</div>` : ''}
    ${goalHtml ? `<div class="char-section">${goalHtml}</div>` : ''}
    <div class="char-section"><div class="sec-title">📖 最近故事</div>${storyHtml}</div>
    <div class="char-section"><div class="sec-title">💭 当前情绪</div>${moodBars}</div>
    <div class="char-section"><div class="sec-title">🏠 身体需求</div>${needsHtml}</div>
    ${loopsHtml ? `<div class="char-section"><div class="sec-title">⚡ 未解心结</div>${loopsHtml}</div>` : ''}
    ${beliefHtml ? `<div class="char-section"><div class="sec-title">🧠 对他人的看法</div>${beliefHtml}</div>` : ''}
  `;
}

// ── Detail Panel (click on canvas agent) ──
function showDetail(agent) {
  selectedAgentId = agent.id;
  document.getElementById('detail-emoji').textContent = agent.emotion?.emoji || '\u{1F636}';
  document.getElementById('detail-name').textContent = agent.name;
  document.getElementById('detail-name').style.color = agent.color;
  document.getElementById('detail-role').textContent = agent.role;
  document.getElementById('detail-emotion').textContent = agent.emotion
    ? `${agent.emotion.type} (${agent.emotion.intensity?.toFixed(1)}/10)` : '';
  document.getElementById('detail-backstory').textContent = agent.backstory || '';

  const needs = agent.needs || {};
  const needDefs = [
    { k: 'hunger', i: '🍎', c: '#e09860' }, { k: 'social', i: '💬', c: '#5b9bd5' },
    { k: 'rest', i: '💤', c: '#5a9e6f' }, { k: 'purpose', i: '⭐', c: '#c8963e' },
  ];
  document.getElementById('detail-needs').innerHTML = needDefs.map(n => {
    const v = needs[n.k] || 50;
    return `<div class="need-row"><span class="need-icon">${n.i}</span>
      <div class="need-bar-wrap"><div class="need-bar" style="width:${v}%;background:${n.c}"></div></div>
      <span class="need-val">${Math.round(v)}</span></div>`;
  }).join('');

  const rels = agent.relationships || {};
  const entries = Object.entries(rels);
  document.getElementById('detail-relationships').innerHTML = entries.length
    ? entries.map(([id, r]) => {
        const cl = r.affinity > 1 ? 'pos' : r.affinity < -1 ? 'neg' : 'neut';
        const stageEmoji = r.stage_emoji || '';
        const stageLabel = r.stage_label || '';
        return `<div class="rel-item ${cl}">
          <span class="rel-name">${stageEmoji} ${r.name}</span>
          <span class="rel-stage">${stageLabel}</span>
          <span class="rel-aff" style="color:${r.affinity>0?'#5a9e6f':'#e07070'}">${r.affinity>0?'+':''}${Number(r.affinity).toFixed(1)}</span>
          <div class="rel-tags">${(r.tags||[]).map(t=>`<span class="rel-tag ${r.affinity>0?'good':'bad'}">${t}</span>`).join('')}</div>
          ${(r.memories||[]).slice(-2).map(m=>`<div class="mem-line">"${m}"</div>`).join('')}
        </div>`;
      }).join('')
    : '<div class="placeholder-text">还没有建立关系</div>';

  const mems = agent.memory || [];
  document.getElementById('detail-memories').innerHTML = mems.length
    ? mems.slice(-5).reverse().map(m => `<div class="mem-line">· ${m}</div>`).join('')
    : '<div class="placeholder-text">暂无记忆</div>';
}

// ── Live Relation Map (panorama for all 5 agents) ──
let relationMapNeedsRedraw = true;
function drawRelationMap() {
  const c = document.getElementById('rel-canvas');
  const wrap = document.getElementById('rel-graph');
  if (!c || !wrap) return;
  const Wc = wrap.clientWidth, Hc = wrap.clientHeight || 300;
  c.width = Wc; c.height = Hc;
  const rctx = c.getContext('2d');
  rctx.clearRect(0, 0, Wc, Hc);

  // Background
  rctx.fillStyle = '#12171e'; rctx.fillRect(0, 0, Wc, Hc);

  const agents = Object.values(agentStates);
  if (agents.length < 2) return;

  // Circular layout
  const cx = Wc / 2, cy = Hc / 2, radius = Math.min(Wc, Hc) * 0.32;
  const positions = {};
  agents.forEach((a, i) => {
    const angle = -Math.PI/2 + (Math.PI*2/agents.length)*i;
    positions[a.id] = { x: cx + Math.cos(angle)*radius, y: cy + Math.sin(angle)*radius, agent: a };
  });

  // Draw connections first (behind nodes)
  const drawnPairs = new Set();
  for (const [aid, a] of Object.entries(agentStates)) {
    const rels = a.relationships || {};
    for (const [rid, r] of Object.entries(rels)) {
      const pairKey = [aid, rid].sort().join('_');
      if (drawnPairs.has(pairKey)) continue;
      drawnPairs.add(pairKey);

      const from = positions[aid], to = positions[rid];
      if (!from || !to) continue;

      const absAff = Math.abs(Number(r.affinity) || 0);
      const isPos = Number(r.affinity) > 0;
      const stage = r.stage || 'stranger';
      const hasAttraction = stage === 'romantic_interest' || stage === 'lover';

      // Line color and style
      let strokeColor, dashPattern = [];
      if (hasAttraction) {
        strokeColor = `rgba(247,120,186,${0.3 + absAff*0.07})`; // pink
        dashPattern = [6, 3];
      } else if (isPos) {
        strokeColor = `rgba(90,158,111,${0.25 + absAff*0.07})`; // green
      } else {
        strokeColor = `rgba(224,112,112,${0.25 + absAff*0.07})`; // red
      }

      // Curved connection
      const mx = (from.x + to.x)/2, my = (from.y + to.y)/2 - 10;
      rctx.strokeStyle = strokeColor;
      rctx.lineWidth = 1 + absAff * 0.6;
      rctx.setLineDash(dashPattern);
      rctx.beginPath(); rctx.moveTo(from.x, from.y); rctx.quadraticCurveTo(mx, my, to.x, to.y); rctx.stroke();
      rctx.setLineDash([]);

      // Stage label at midpoint
      if (stage !== 'stranger' && stage !== 'acquaintance') {
        rctx.fillStyle = '#8892a0'; rctx.font = '8px "Noto Sans SC"'; rctx.textAlign = 'center';
        rctx.fillText(r.stage_label || '', mx, my - 4);
      }
    }
  }

  // Draw nodes
  for (const [aid, pos] of Object.entries(positions)) {
    const a = pos.agent;
    // Pulse for selected
    if (aid === (charViewAgentId || selectedAgentId)) {
      rctx.shadowColor = a.color; rctx.shadowBlur = 15;
    }
    rctx.fillStyle = a.color; rctx.beginPath(); rctx.arc(pos.x, pos.y, 12, 0, Math.PI*2); rctx.fill();
    rctx.shadowColor = 'transparent'; rctx.shadowBlur = 0;
    rctx.strokeStyle = '#1a1f2a'; rctx.lineWidth = 2; rctx.stroke();

    rctx.fillStyle = '#e2e8f0'; rctx.font = '9px "Noto Sans SC"'; rctx.textAlign = 'center';
    rctx.fillText(a.name, pos.x, pos.y + 22);
  }
}

// ── Daily Digest ──
function generateDailyReport() {
  const agents = Object.values(agentStates);
  if (!agents.length) return;

  // Count speeches per agent
  const speechCount = {};
  for (const e of eventLog) { if (e.type === 'speech') speechCount[e.who] = (speechCount[e.who]||0) + 1; }
  const mostActive = Object.entries(speechCount).sort((a,b) => b[1]-a[1])[0];

  // Count gossip
  const gossipCount = eventLog.filter(e => e.gossipAbout).length;

  // Find loneliest
  let loneliest = null, maxLonely = 0;
  for (const a of agents) {
    const mv = a.mood_vector || {};
    if ((mv.loneliness||0) > maxLonely) { maxLonely = mv.loneliness; loneliest = a; }
  }

  // Relationship changes
  const relChanges = [];
  for (const a of agents) {
    const snap = relationSnapshots[a.id] || {};
    const current = a.relationships || {};
    for (const [rid, r] of Object.entries(current)) {
      const oldAff = snap[rid]?.affinity || 0;
      const newAff = Number(r.affinity) || 0;
      const oldStage = snap[rid]?.stage || 'stranger';
      const newStage = r.stage || 'stranger';
      if (Math.abs(newAff - oldAff) > 2 || oldStage !== newStage) {
        const otherName = Object.values(agentStates).find(x => x.id === rid)?.name || rid;
        relChanges.push({ from: a.name, to: otherName, oldAff, newAff, oldStage, newStage });
      }
    }
  }

  // Build report
  let report = `<div class="digest-title">📰 小镇日报 — 第${dayNumber}天</div>`;
  report += `<div class="digest-phase">${timeLabel}</div>`;

  if (mostActive) {
    report += `<p>今天最活跃的是 <b style="color:${agents.find(a=>a.name===mostActive[0])?.color||'#58a6ff'}">${mostActive[0]}</b>（${mostActive[1]}次对话）。</p>`;
  }
  if (gossipCount > 0) {
    report += `<p>小镇上流传了 <b>${gossipCount}</b> 条流言。</p>`;
  }
  if (loneliest && maxLonely > 5) {
    report += `<p><b style="color:${loneliest.color}">${loneliest.name}</b> 今天感到最孤独（孤独感 ${maxLonely.toFixed(1)}）。</p>`;
  }
  if (relChanges.length > 0) {
    report += `<div class="sec-title">关系变化</div>`;
    report += relChanges.map(rc => `<div class="digest-rel-change">
      <b>${rc.from}</b> → <b>${rc.to}</b>:
      <span class="rel-stage-badge">${rc.oldStage}</span> → <span class="rel-stage-badge">${rc.newStage}</span>
      (${rc.oldAff>0?'+':''}${rc.oldAff.toFixed(1)} → ${rc.newAff>0?'+':''}${rc.newAff.toFixed(1)})
    </div>`).join('');
  }

  // Show in modal
  const modal = document.getElementById('digest-modal');
  const body = document.getElementById('digest-body');
  if (modal && body) {
    body.innerHTML = report;
    modal.style.display = 'flex';
  }
}
function closeDigest() {
  const modal = document.getElementById('digest-modal');
  if (modal) modal.style.display = 'none';
}

// ── Tabs ──
document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('#tabs button').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('#tabs button').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      document.querySelectorAll('.tab-panel').forEach(t => t.classList.remove('active'));
      document.getElementById(btn.dataset.tab).classList.add('active');
      if (btn.dataset.tab === 'tab-relations') setTimeout(() => drawRelationMap(), 100);
    });
  });

  // Character view buttons
  document.querySelectorAll('.char-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      showCharacterView(btn.dataset.aid);
    });
  });

  // Filter buttons
  document.getElementById('filter-important')?.addEventListener('click', function() {
    storyFilterLevel = 3; renderStoryFeed();
    document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active')); this.classList.add('active');
  });
  document.getElementById('filter-all')?.addEventListener('click', function() {
    storyFilterLevel = 2; renderStoryFeed();
    document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active')); this.classList.add('active');
  });
});

// ============================================================
// 9. CONTROLS
// ============================================================
function togglePause() { if (ws && ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify({ type: 'toggle_pause' })); }
function setSpeed(s) { if (ws && ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify({ type: 'set_speed', speed: s })); }
function updatePauseUI() {
  const btn = document.getElementById('btn-pause'); const dot = document.getElementById('status-dot');
  if (btn) btn.textContent = paused ? '▶' : '⏸';
  if (dot) { if (paused) dot.classList.add('paused'); else dot.classList.remove('paused'); }
}
function updateSpeedUI() {
  const label = document.getElementById('speed-label'); if (label) label.textContent = `${tickSpeed}s/tick`;
  ['btn-s1','btn-s2','btn-s3'].forEach(id => { const b = document.getElementById(id); if (b) b.classList.remove('active'); });
  if (tickSpeed >= 7) document.getElementById('btn-s1')?.classList.add('active');
  else if (tickSpeed <= 3) document.getElementById('btn-s3')?.classList.add('active');
  else document.getElementById('btn-s2')?.classList.add('active');
}

// ============================================================
// 10. HERO PARTICLES
// ============================================================
function initHeroParticles() {
  const hc = document.getElementById('hero-particles');
  if (!hc) return;
  hc.width = hc.parentElement.offsetWidth; hc.height = hc.parentElement.offsetHeight;
  const hctx = hc.getContext('2d');
  const hps = [];
  for (let i = 0; i < 50; i++) {
    hps.push({
      x: Math.random() * hc.width, y: Math.random() * hc.height,
      vx: (Math.random() - 0.5) * 0.35, vy: -(Math.random() * 0.5 + 0.15),
      r: Math.random() * 2 + 0.8, life: Math.random() * 180 + 60, maxLife: 240,
      color: ['#d4b896','#c8d8b0','#e8d0c0','#d0c8e0','#e0d8c8'][Math.floor(Math.random()*5)],
    });
  }

  function anim() {
    if (!hc.isConnected) return;
    hctx.clearRect(0, 0, hc.width, hc.height);
    for (const p of hps) {
      p.x += p.vx; p.y += p.vy; p.life--;
      if (p.life <= 0) { p.x = Math.random()*hc.width; p.y = hc.height + 10; p.life = p.maxLife; }
      hctx.globalAlpha = Math.min(1, p.life / 100) * 0.45;
      hctx.fillStyle = p.color; hctx.beginPath(); hctx.arc(p.x, p.y, p.r, 0, Math.PI*2); hctx.fill();
    }
    hctx.globalAlpha = 1;
    requestAnimationFrame(anim);
  }
  requestAnimationFrame(anim);
  window.addEventListener('resize', () => { hc.width = hc.parentElement.offsetWidth; hc.height = hc.parentElement.offsetHeight; });
}

// ============================================================
// 11. NAV SCROLL
// ============================================================
function initNavScroll() {
  const nav = document.getElementById('nav');
  window.addEventListener('scroll', () => {
    if (nav) nav.classList.toggle('scrolled', window.scrollY > 40);
  });
  document.querySelectorAll('.nav-links a[href^="#"]').forEach(link => {
    link.addEventListener('click', (e) => {
      e.preventDefault();
      const t = document.querySelector(link.getAttribute('href'));
      if (t) t.scrollIntoView({ behavior: 'smooth' });
    });
  });
}

// ============================================================
// 12. INIT
// ============================================================
function init() {
  loadAssets();
  prerenderTiles();
  // Spawn fireflies
  for (let i = 0; i < 55; i++) {
    fireflies.push({
      x: Math.random() * W, y: Math.random() * H,
      vx: (Math.random() - 0.5) * 0.25, vy: (Math.random() - 0.5) * 0.25,
      r: 1.2 + Math.random() * 1.5, phase: Math.random() * Math.PI * 2,
      glow: 0,
    });
  }
  connectWS();
  initHeroParticles();
  initNavScroll();
  requestAnimationFrame(mainRender);
}

document.addEventListener('DOMContentLoaded', init);
