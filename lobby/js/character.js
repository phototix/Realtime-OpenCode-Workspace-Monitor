import { CharacterAnimator } from "./animation.js";

export class Character {
  constructor(spriteSheet, x, y, animationConfig = {}) {
    this.x = x;
    this.y = y;
    this.speed = 120;
    this.lastDirX = 1;
    this.lastDirY = 0;
    this.facingX = 1;
    this.facingY = 0;

    this.pathPixels = [];
    this.currentMap = null;

    this.animator = new CharacterAnimator(spriteSheet, {
      columns: animationConfig.columns ?? 6,
      rows: animationConfig.rows ?? 8,
      fps: animationConfig.fps ?? 10,
      frameSequence: animationConfig.frameSequence ?? [0, 1, 2, 3, 4, 5, 4, 3, 2, 1],
      directionRows:
        animationConfig.directionRows ?? {
          up: 0,
          "up-right": 1,
          right: 2,
          "down-right": 3,
          down: 4,
          "down-left": 5,
          left: 6,
          "up-left": 7,
        },
      colorKeyBlack: animationConfig.colorKeyBlack ?? false,
    });

      this.idleAnimators = (animationConfig.idleAnimations ?? []).map((idleConfig) => {
        const columns = idleConfig.columns ?? 5;
        const rows = idleConfig.rows ?? 5;
        const totalFrames = columns * rows;
        return new CharacterAnimator(idleConfig.spriteSheet, {
          columns,
          rows,
          fps: idleConfig.fps ?? 8,
          frameSequence:
            idleConfig.frameSequence ?? Array.from({ length: totalFrames }, (_, i) => i),
          sequenceIsGridIndex: idleConfig.sequenceIsGridIndex ?? true,
          directionRows: idleConfig.directionRows ?? { down: 0 },
          colorKeyBlack: idleConfig.colorKeyBlack ?? false,
        });
      });
      this.activeAnimator = this.animator;
      this.currentIdleAnimator = null;
      this.idleActionTimer = 0;
      this.idleActionMinDuration = animationConfig.idleActionMinDuration ?? 3.8;
      this.idleActionMaxDuration = animationConfig.idleActionMaxDuration ?? 6.5;
  }

  setPath(cellPath, map) {
    this.currentMap = map;
    const smoothedPath = this.smoothCellPath(cellPath, map);
    this.pathPixels = smoothedPath.map((cell) => map.cellToWorldCenter(cell.cx, cell.cy));
    if (this.pathPixels.length > 0) {
      this.pathPixels.shift(); // first point is current tile.
    }
  }

  update(dt) {
    if (this.pathPixels.length === 0) {
      this.updateIdleState(dt);
      this.animator.setMoving(false);
      return;
    }

    this.currentIdleAnimator?.setMoving(false);
    this.currentIdleAnimator = null;
    this.activeAnimator = this.animator;

    // Runtime look-ahead: skip near waypoints if a farther waypoint is directly reachable.
    if (this.currentMap && this.pathPixels.length > 1) {
      const here = this.currentMap.worldToCell(this.x, this.y);
      while (this.pathPixels.length > 1) {
        const candidate = this.pathPixels[1];
        const targetCell = this.currentMap.worldToCell(candidate.x, candidate.y);
        if (!this.hasLineOfSight(here, targetCell, this.currentMap)) {
          break;
        }
        this.pathPixels.shift();
      }
    }

    const target = this.pathPixels[0];
    const dx = target.x - this.x;
    const dy = target.y - this.y;
    const dist = Math.hypot(dx, dy);

    if (dist < 1.2) {
      this.x = target.x;
      this.y = target.y;
      this.pathPixels.shift();
      if (this.pathPixels.length > 0) {
        const next = this.pathPixels[0];
        const ndx = next.x - this.x;
        const ndy = next.y - this.y;
        const nDist = Math.hypot(ndx, ndy);
        if (nDist > 0.0001) {
          this.lastDirX = ndx / nDist;
          this.lastDirY = ndy / nDist;
          this.facingX = this.lastDirX;
          this.facingY = this.lastDirY;
          this.animator.setDirection(this.vectorToDirection(this.facingX, this.facingY));
        }
      }
      this.animator.setMoving(this.pathPixels.length > 0);
      this.animator.update(dt);
      return;
    }

    const dirX = dx / dist;
    const dirY = dy / dist;

    const step = this.speed * dt;
    const move = Math.min(step, dist);
    this.x += dirX * move;
    this.y += dirY * move;

    this.lastDirX = dirX;
    this.lastDirY = dirY;
    const blend = 0.22;
    this.facingX = this.facingX * (1 - blend) + this.lastDirX * blend;
    this.facingY = this.facingY * (1 - blend) + this.lastDirY * blend;
    const len = Math.hypot(this.facingX, this.facingY);
    if (len > 0.0001) {
      this.facingX /= len;
      this.facingY /= len;
    }

    this.animator.setDirection(this.vectorToDirection(this.facingX, this.facingY));
    this.animator.setMoving(true);
    this.animator.update(dt);
  }

  draw(ctx) {
    this.activeAnimator.draw(ctx, this.x, this.y);
  }

  updateIdleState(dt) {
    if (this.idleAnimators.length === 0) {
      this.activeAnimator = this.animator;
      this.animator.setMoving(false);
      this.animator.update(dt);
      return;
    }

    this.idleActionTimer -= dt;
    if (!this.currentIdleAnimator || this.idleActionTimer <= 0) {
      this.currentIdleAnimator?.setMoving(false);
      this.currentIdleAnimator = this.pickRandomIdleAnimator();
      this.idleActionTimer = this.randomRange(this.idleActionMinDuration, this.idleActionMaxDuration);
    }

    this.activeAnimator = this.currentIdleAnimator;
    this.currentIdleAnimator.setMoving(true);
    this.currentIdleAnimator.update(dt);
  }

  pickRandomIdleAnimator() {
    const index = Math.floor(Math.random() * this.idleAnimators.length);
    return this.idleAnimators[index] ?? this.idleAnimators[0];
  }

  randomRange(min, max) {
    return min + Math.random() * (max - min);
  }

  vectorToDirection(dx, dy) {
    // Ignore tiny vectors to avoid random facing flips near node transitions.
    const deadZone = 0.001;
    if (Math.abs(dx) < deadZone && Math.abs(dy) < deadZone) {
      return this.animator.direction;
    }

    // Screen space: +x right, +y down.
    // Use stable sectoring with explicit boundaries for 8 directions.
    const angle = Math.atan2(dy, dx);
    const eighth = Math.PI / 8;

    if (angle >= -eighth && angle < eighth) return "right";
    if (angle >= eighth && angle < 3 * eighth) return "down-right";
    if (angle >= 3 * eighth && angle < 5 * eighth) return "down";
    if (angle >= 5 * eighth && angle < 7 * eighth) return "down-left";
    if (angle >= 7 * eighth || angle < -7 * eighth) return "left";
    if (angle >= -7 * eighth && angle < -5 * eighth) return "up-left";
    if (angle >= -5 * eighth && angle < -3 * eighth) return "up";
    return "up-right";
  }

  smoothCellPath(cellPath, map) {
    if (!cellPath || cellPath.length <= 2) {
      return cellPath ?? [];
    }

    const out = [cellPath[0]];
    let i = 0;

    while (i < cellPath.length - 1) {
      let furthest = i + 1;
      for (let j = cellPath.length - 1; j > i + 1; j -= 1) {
        if (this.hasLineOfSight(cellPath[i], cellPath[j], map)) {
          furthest = j;
          break;
        }
      }

      out.push(cellPath[furthest]);
      i = furthest;
    }

    return out;
  }

  hasLineOfSight(a, b, map) {
    const x0 = a.cx;
    const y0 = a.cy;
    const x1 = b.cx;
    const y1 = b.cy;

    const dx = x1 - x0;
    const dy = y1 - y0;
    const steps = Math.max(Math.abs(dx), Math.abs(dy)) * 2;

    if (steps === 0) {
      return map.isWalkableCell(x0, y0);
    }

    for (let i = 0; i <= steps; i += 1) {
      const t = i / steps;
      const x = Math.round(x0 + dx * t);
      const y = Math.round(y0 + dy * t);
      if (!map.isWalkableCell(x, y)) {
        return false;
      }
    }

    return true;
  }
}
