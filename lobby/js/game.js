import { OfficeMap } from "./map.js";
import { AStar } from "./astar.js";
import { Character } from "./character.js";
import { WanderingNPC } from "./npc.js";
import { buildSceneLayers } from "./assetsComposer.js";

const canvas = document.getElementById("gameCanvas");
const ctx = canvas.getContext("2d");
const statusEl = document.getElementById("status");

let officeEmptyImage;
let assetsSheetImage;
let officeReferenceImage;
let walkingSheet;
let officeMap;
let character;
let npc;
let debugGrid = false;
let latestPath = [];
let staticAssets = [];
let sceneCompositeCanvas;
const WALKING_FULL_CACHE_BUST = "v=20260717-02";
const IDLE_CACHE_BUST = "v=20260720-01";
const IDLE_STANDARD_CANVAS_SIZE = 1280;
const IDLE_SHEET_CANDIDATES = [
  "lobby/assets/idle-drinking.png",
  "lobby/assets/idle-playphone.png",
];
const MANUAL_PATH_BLOCKERS = [
  // sofa area
  { x: 632, y: 547, width: 132, height: 78 },
  // coffee table on rug
  { x: 666, y: 602, width: 88, height: 66 },
  // bookshelf right of sofa (reported issue)
  { x: 770, y: 535, width: 86, height: 115 },
  // planter near rug-left
  { x: 603, y: 594, width: 54, height: 70 },
];

function loadImage(src) {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.onload = () => resolve(img);
    img.onerror = () => reject(new Error(`Failed to load image: ${src}`));
    img.src = src;
  });
}

async function loadIdleSheets() {
  const settled = await Promise.allSettled(
    IDLE_SHEET_CANDIDATES.map((src) => loadImage(`${src}?${IDLE_CACHE_BUST}`))
  );

  return settled
    .filter((entry) => entry.status === "fulfilled")
    .map((entry) => entry.value);
}

function buildIdleAnimationConfig(idleSheets) {
  return idleSheets.map((sheet) => ({
    spriteSheet: sheet,
    columns: 5,
    rows: 5,
    fps: 9,
    frameSequence: Array.from({ length: 25 }, (_, i) => i),
    sequenceIsGridIndex: true,
    sheetScale: IDLE_STANDARD_CANVAS_SIZE / sheet.width,
    colorKeyBlack: false,
  }));
}

function screenToWorld(event) {
  const rect = canvas.getBoundingClientRect();
  const sx = (event.clientX - rect.left) / rect.width;
  const sy = (event.clientY - rect.top) / rect.height;
  return {
    x: sx * canvas.width,
    y: sy * canvas.height,
  };
}

function drawPath(pathCells) {
  if (!pathCells || pathCells.length < 2) {
    return;
  }

  ctx.save();
  ctx.strokeStyle = "rgba(14, 165, 233, 0.9)";
  ctx.lineWidth = 3;
  ctx.beginPath();

  pathCells.forEach((cell, index) => {
    const p = officeMap.cellToWorldCenter(cell.cx, cell.cy);
    if (index === 0) {
      ctx.moveTo(p.x, p.y);
    } else {
      ctx.lineTo(p.x, p.y);
    }
  });

  ctx.stroke();
  ctx.restore();
}

function drawActorsWithOcclusion(actors, assets) {
  const sortedActors = actors.filter(Boolean).sort((a, b) => a.y - b.y);
  const frontAssets = assets
    .filter((asset) => asset.occluder)
    .slice()
    .sort((a, b) => a.baseY - b.baseY);

  let frontIndex = 0;
  for (const actor of sortedActors) {
    while (frontIndex < frontAssets.length && frontAssets[frontIndex].baseY <= actor.y) {
      const asset = frontAssets[frontIndex];
      ctx.drawImage(asset.sprite, asset.x, asset.y, asset.width, asset.height);
      frontIndex += 1;
    }
    actor.draw(ctx);
  }

  while (frontIndex < frontAssets.length) {
    const asset = frontAssets[frontIndex];
    ctx.drawImage(asset.sprite, asset.x, asset.y, asset.width, asset.height);
    frontIndex += 1;
  }
}

function render() {
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  ctx.drawImage(officeEmptyImage, 0, 0);

  // Always-behind assets (walls/large structures).
  for (const asset of staticAssets) {
    if (asset.occluder) {
      continue;
    }
    ctx.drawImage(asset.sprite, asset.x, asset.y, asset.width, asset.height);
  }

  if (debugGrid) {
    officeMap.drawDebugGrid(ctx, 0.22);
  }

  drawPath(latestPath);
  drawActorsWithOcclusion([character, npc], staticAssets);
}

let lastTs = 0;
function loop(ts) {
  if (!lastTs) {
    lastTs = ts;
  }

  const dt = Math.min((ts - lastTs) / 1000, 0.032);
  lastTs = ts;

  character.update(dt);
  npc?.update(dt, officeMap, character);
  render();
  requestAnimationFrame(loop);
}

async function bootstrap() {
  try {
    const [idleSheets] = await Promise.all([loadIdleSheets()]);

    [officeEmptyImage, assetsSheetImage, officeReferenceImage, walkingSheet] = await Promise.all([
      loadImage("lobby/assets/office-empty.png"),
      loadImage("lobby/assets/assets.png"),
      loadImage("lobby/assets/office.png"),
      loadImage(`lobby/assets/walking-full.png?${WALKING_FULL_CACHE_BUST}`),
    ]);
    const idleAnimations = buildIdleAnimationConfig(idleSheets);

    canvas.width = officeEmptyImage.width;
    canvas.height = officeEmptyImage.height;

    const layers = buildSceneLayers({
      officeEmptyImage,
      assetsSheetImage,
      officeReferenceImage,
    });

    staticAssets = layers.staticAssets;
    sceneCompositeCanvas = layers.compositeCanvas;

    officeMap = new OfficeMap(sceneCompositeCanvas, 12);
    officeMap.analyzeBoundaries();
    officeMap.applyBlockedRects(MANUAL_PATH_BLOCKERS, {
      padding: 1,
      footprintTopRatio: 0.38,
    });

    const spawn = officeMap.findNearestWalkable(
      officeMap.worldToCell(canvas.width * 0.5, canvas.height * 0.6)
    );

    if (!spawn) {
      throw new Error("No walkable spawn point found. Check map boundary thresholds.");
    }

    const spawnWorld = officeMap.cellToWorldCenter(spawn.cx, spawn.cy);
    character = new Character(walkingSheet, spawnWorld.x, spawnWorld.y, {
      columns: 6,
      rows: 8,
      fps: 12,
      frameSequence: [0, 1, 2, 3, 4, 5, 4, 3, 2, 1],
      directionRows: {
        up: 0,
        "up-right": 1,
        right: 2,
        "down-right": 3,
        down: 4,
        "down-left": 5,
        left: 6,
        "up-left": 7,
      },
      colorKeyBlack: false,
      idleAnimations,
      idleActionMinDuration: 3.6,
      idleActionMaxDuration: 6.2,
    });

    const npcSpawn = findNpcSpawn(officeMap, spawn);
    const npcWorld = officeMap.cellToWorldCenter(npcSpawn.cx, npcSpawn.cy);
    npc = new WanderingNPC(walkingSheet, npcWorld.x, npcWorld.y, {
      columns: 6,
      rows: 8,
      fps: 12,
      frameSequence: [0, 1, 2, 3, 4, 5, 4, 3, 2, 1],
      directionRows: {
        up: 0,
        "up-right": 1,
        right: 2,
        "down-right": 3,
        down: 4,
        "down-left": 5,
        left: 6,
        "up-left": 7,
      },
      colorKeyBlack: false,
      idleAnimations,
      idleActionMinDuration: 3.9,
      idleActionMaxDuration: 6.8,
      minWait: 0.8,
      maxWait: 2.3,
      minPathLength: 8,
      minCellDistance: 14,
    });
    npc.pickAndWalk(officeMap, character);

    canvas.addEventListener("click", (event) => {
      const world = screenToWorld(event);
      const start = officeMap.worldToCell(character.x, character.y);
      const clicked = officeMap.worldToCell(world.x, world.y);
      const target = officeMap.findNearestWalkable(clicked);

      if (!target) {
        statusEl.textContent = "That point is not reachable (blocked area).";
        latestPath = [];
        return;
      }

      const path = AStar.findPath(officeMap, start, target, true);
      if (path.length === 0) {
        statusEl.textContent = "No path found to the selected point.";
        latestPath = [];
        return;
      }

      latestPath = path;
      character.setPath(path, officeMap);
      statusEl.textContent = `Walking to (${target.cx}, ${target.cy}) via ${path.length} nodes.`;
    });

    window.addEventListener("keydown", (event) => {
      if (event.key.toLowerCase() === "d") {
        debugGrid = !debugGrid;
        statusEl.textContent = debugGrid
          ? "Debug grid: ON (walkable cells highlighted)."
          : "Debug grid: OFF.";
      }
    });

    statusEl.textContent = `Ready. Click to move. Assets placed: ${layers.stats.placedAssets}. Press D for debug grid.`;
    requestAnimationFrame(loop);
  } catch (error) {
    statusEl.textContent = `Error: ${error.message}`;
    console.error(error);
  }
}

function findNpcSpawn(map, playerSpawn) {
  for (let i = 0; i < 120; i += 1) {
    const cx = Math.floor(Math.random() * map.gridWidth);
    const cy = Math.floor(Math.random() * map.gridHeight);
    if (!map.isWalkableCell(cx, cy)) {
      continue;
    }

    const dx = cx - playerSpawn.cx;
    const dy = cy - playerSpawn.cy;
    if (Math.hypot(dx, dy) < 18) {
      continue;
    }

    return { cx, cy };
  }

  return { cx: playerSpawn.cx + 10, cy: playerSpawn.cy + 10 };
}

bootstrap();
