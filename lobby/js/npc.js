import { Character } from "./character.js";
import { AStar } from "./astar.js";

export class WanderingNPC {
  constructor(spriteSheet, x, y, animationConfig = {}) {
    this.character = new Character(spriteSheet, x, y, animationConfig);
    this.state = "walking";
    this.waitTimer = 0;
    this.minWait = animationConfig.minWait ?? 0.8;
    this.maxWait = animationConfig.maxWait ?? 2.2;
    this.minPathLength = animationConfig.minPathLength ?? 8;
    this.minCellDistance = animationConfig.minCellDistance ?? 12;
    this.maxAttempts = animationConfig.maxAttempts ?? 40;
    this.lastTarget = null;
    this.avoidPlayerRadius = animationConfig.avoidPlayerRadius ?? 16;
    this.zoneLingerBoost = animationConfig.zoneLingerBoost ?? 1.75;
    this.zones = animationConfig.zones ?? [
      { name: "desks", cx: 30, cy: 50, radius: 18, weight: 1.4, linger: 0.8 },
      { name: "meeting", cx: 58, cy: 26, radius: 16, weight: 0.9, linger: 1.2 },
      { name: "pantry", cx: 88, cy: 36, radius: 16, weight: 2.0, linger: 2.5 },
      { name: "lounge", cx: 82, cy: 67, radius: 18, weight: 2.3, linger: 3.2 },
      { name: "entry", cx: 42, cy: 74, radius: 14, weight: 0.7, linger: 0.7 },
    ];
  }

  get x() {
    return this.character.x;
  }

  get y() {
    return this.character.y;
  }

  update(dt, map, player = null) {
    if (this.state === "waiting") {
      this.waitTimer -= dt;
      this.character.update(dt);
      if (this.waitTimer <= 0) {
        this.state = "walking";
        this.pickAndWalk(map, player);
      }
      return;
    }

    if (player && this.isTooCloseToPlayer(player)) {
      this.character.pathPixels = [];
      this.state = "waiting";
      this.waitTimer = this.randomRange(this.minWait, this.maxWait) + 0.6;
      this.character.update(dt);
      return;
    }

    this.character.update(dt);

    if (this.character.pathPixels.length === 0) {
      this.state = "waiting";
      this.waitTimer = this.getWaitTimeForCurrentZone(map) ?? this.randomRange(this.minWait, this.maxWait);
    }
  }

  draw(ctx) {
    this.character.draw(ctx);
  }

  pickAndWalk(map, player = null) {
    const start = map.worldToCell(this.character.x, this.character.y);

    for (let attempt = 0; attempt < this.maxAttempts; attempt += 1) {
      const target = this.pickSmartTargetCell(map, start, player);
      if (!target) {
        continue;
      }

      const path = AStar.findPath(map, start, target, true);
      if (path.length < this.minPathLength) {
        continue;
      }

      this.lastTarget = target;
      this.character.setPath(path, map);
      return;
    }

    // If no good path found, pause and try again later.
    this.state = "waiting";
    this.waitTimer = this.randomRange(this.minWait, this.maxWait);
  }

  pickSmartTargetCell(map, start, player = null) {
    const zone = this.pickWeightedZone();
    for (let i = 0; i < 24; i += 1) {
      const cx = this.clampInt(
        Math.round(zone.cx + this.randomRange(-zone.radius, zone.radius)),
        0,
        map.gridWidth - 1
      );
      const cy = this.clampInt(
        Math.round(zone.cy + this.randomRange(-zone.radius, zone.radius)),
        0,
        map.gridHeight - 1
      );

      if (!map.isWalkableCell(cx, cy)) {
        continue;
      }

      const dx = cx - start.cx;
      const dy = cy - start.cy;
      const dist = Math.hypot(dx, dy);
      if (dist < this.minCellDistance) {
        continue;
      }

      if (player) {
        const pdx = cx - map.worldToCell(player.x, player.y).cx;
        const pdy = cy - map.worldToCell(player.x, player.y).cy;
        const playerDist = Math.hypot(pdx, pdy);
        if (playerDist < this.avoidPlayerRadius) {
          continue;
        }
      }

      return { cx, cy, zone };
    }

    return null;
  }

  pickWeightedZone() {
    const total = this.zones.reduce((sum, z) => sum + z.weight, 0);
    let roll = Math.random() * total;
    for (const zone of this.zones) {
      roll -= zone.weight;
      if (roll <= 0) {
        return zone;
      }
    }
    return this.zones[this.zones.length - 1];
  }

  getWaitTimeForCurrentZone(map) {
    if (!this.lastTarget) {
      return null;
    }

    const zone = this.zones.find((z) => {
      const dx = this.lastTarget.cx - z.cx;
      const dy = this.lastTarget.cy - z.cy;
      return Math.hypot(dx, dy) <= z.radius;
    });

    if (!zone) {
      return null;
    }

    return this.randomRange(this.minWait, this.maxWait) + zone.linger * this.zoneLingerBoost;
  }

  isTooCloseToPlayer(player) {
    const dx = this.x - player.x;
    const dy = this.y - player.y;
    return Math.hypot(dx, dy) < this.avoidPlayerRadius * 12;
  }

  clampInt(value, min, max) {
    return Math.max(min, Math.min(max, value));
  }

  randomRange(min, max) {
    return min + Math.random() * (max - min);
  }
}
