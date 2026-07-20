export class OfficeMap {
  constructor(image, cellSize = 12) {
    this.image = image;
    this.cellSize = cellSize;
    this.width = image.width;
    this.height = image.height;
    this.gridWidth = Math.ceil(this.width / this.cellSize);
    this.gridHeight = Math.ceil(this.height / this.cellSize);

    this.walkable = Array.from({ length: this.gridHeight }, () =>
      Array(this.gridWidth).fill(false)
    );

    this.buffer = document.createElement("canvas");
    this.buffer.width = this.width;
    this.buffer.height = this.height;
    this.bufferCtx = this.buffer.getContext("2d", { willReadFrequently: true });
    this.bufferCtx.drawImage(this.image, 0, 0);
  }

  analyzeBoundaries() {
    const img = this.bufferCtx.getImageData(0, 0, this.width, this.height);
    const pixels = img.data;

    const sampleColor = (nx, ny) => {
      const x = Math.max(0, Math.min(this.width - 1, Math.floor(nx * this.width)));
      const y = Math.max(0, Math.min(this.height - 1, Math.floor(ny * this.height)));
      const i = (y * this.width + x) * 4;
      return [pixels[i], pixels[i + 1], pixels[i + 2]];
    };

    // Seed floor tones from known office floor regions (gray, orange, green).
    const floorPalette = [
      sampleColor(0.52, 0.56),
      sampleColor(0.73, 0.46),
      sampleColor(0.66, 0.68),
      sampleColor(0.36, 0.67),
    ];

    const colorDistance = (a, b) => {
      const dr = a[0] - b[0];
      const dg = a[1] - b[1];
      const db = a[2] - b[2];
      return Math.sqrt(dr * dr + dg * dg + db * db);
    };

    const step = 2;
    for (let gy = 0; gy < this.gridHeight; gy += 1) {
      for (let gx = 0; gx < this.gridWidth; gx += 1) {
        const sx = gx * this.cellSize;
        const sy = gy * this.cellSize;
        const ex = Math.min(sx + this.cellSize, this.width);
        const ey = Math.min(sy + this.cellSize, this.height);

        let count = 0;
        let alphaSum = 0;
        let rSum = 0;
        let gSum = 0;
        let bSum = 0;

        for (let y = sy; y < ey; y += step) {
          for (let x = sx; x < ex; x += step) {
            const idx = (y * this.width + x) * 4;
            const a = pixels[idx + 3];
            alphaSum += a;
            rSum += pixels[idx];
            gSum += pixels[idx + 1];
            bSum += pixels[idx + 2];
            count += 1;
          }
        }

        if (count === 0) {
          continue;
        }

        const avg = [rSum / count, gSum / count, bSum / count];
        const avgAlpha = alphaSum / count;

        const minDist = floorPalette.reduce((best, floorColor) => {
          return Math.min(best, colorDistance(avg, floorColor));
        }, Number.POSITIVE_INFINITY);

        const luminance = 0.2126 * avg[0] + 0.7152 * avg[1] + 0.0722 * avg[2];
        const floorLike = minDist < 68 && luminance > 38;
        const visible = avgAlpha > 20;

        this.walkable[gy][gx] = floorLike && visible;
      }
    }

    // Keep only floor area connected to center (prevents walking in blue sky/background).
    const origin = this.findNearestWalkable(this.worldToCell(this.width * 0.52, this.height * 0.6));
    if (origin) {
      this.keepConnectedRegion(origin.cx, origin.cy);
    }

    // Inflate static obstacles by one cell for smoother collision avoidance.
    this.erodeWalkable(1);
  }

  keepConnectedRegion(startX, startY) {
    const visited = Array.from({ length: this.gridHeight }, () =>
      Array(this.gridWidth).fill(false)
    );
    const queue = [[startX, startY]];
    visited[startY][startX] = true;

    const dirs = [
      [1, 0],
      [-1, 0],
      [0, 1],
      [0, -1],
    ];

    while (queue.length > 0) {
      const [x, y] = queue.shift();
      for (const [dx, dy] of dirs) {
        const nx = x + dx;
        const ny = y + dy;
        if (!this.inBounds(nx, ny) || visited[ny][nx] || !this.walkable[ny][nx]) {
          continue;
        }
        visited[ny][nx] = true;
        queue.push([nx, ny]);
      }
    }

    for (let y = 0; y < this.gridHeight; y += 1) {
      for (let x = 0; x < this.gridWidth; x += 1) {
        this.walkable[y][x] = this.walkable[y][x] && visited[y][x];
      }
    }
  }

  erodeWalkable(radius = 1) {
    const clone = this.walkable.map((row) => row.slice());
    for (let y = 0; y < this.gridHeight; y += 1) {
      for (let x = 0; x < this.gridWidth; x += 1) {
        if (!clone[y][x]) {
          continue;
        }

        let nearObstacle = false;
        for (let oy = -radius; oy <= radius && !nearObstacle; oy += 1) {
          for (let ox = -radius; ox <= radius; ox += 1) {
            const nx = x + ox;
            const ny = y + oy;
            if (!this.inBounds(nx, ny) || !clone[ny][nx]) {
              nearObstacle = true;
              break;
            }
          }
        }

        if (nearObstacle) {
          this.walkable[y][x] = false;
        }
      }
    }
  }

  inBounds(cx, cy) {
    return cx >= 0 && cy >= 0 && cx < this.gridWidth && cy < this.gridHeight;
  }

  isWalkableCell(cx, cy) {
    return this.inBounds(cx, cy) && this.walkable[cy][cx];
  }

  worldToCell(x, y) {
    return {
      cx: Math.max(0, Math.min(this.gridWidth - 1, Math.floor(x / this.cellSize))),
      cy: Math.max(0, Math.min(this.gridHeight - 1, Math.floor(y / this.cellSize))),
    };
  }

  cellToWorldCenter(cx, cy) {
    return {
      x: cx * this.cellSize + this.cellSize * 0.5,
      y: cy * this.cellSize + this.cellSize * 0.5,
    };
  }

  findNearestWalkable(start) {
    if (!start) {
      return null;
    }

    if (this.isWalkableCell(start.cx, start.cy)) {
      return start;
    }

    const maxRadius = Math.max(this.gridWidth, this.gridHeight);
    for (let r = 1; r < maxRadius; r += 1) {
      for (let y = -r; y <= r; y += 1) {
        for (let x = -r; x <= r; x += 1) {
          const cx = start.cx + x;
          const cy = start.cy + y;
          if (!this.isWalkableCell(cx, cy)) {
            continue;
          }
          return { cx, cy };
        }
      }
    }

    return null;
  }

  applyBlockedRects(rects, options = {}) {
    if (!Array.isArray(rects) || rects.length === 0) {
      return;
    }

    const padding = options.padding ?? 2;
    const footprintTopRatio = options.footprintTopRatio ?? 0.45;

    for (const rect of rects) {
      const left = Math.max(0, rect.x - padding);
      const right = Math.min(this.width - 1, rect.x + rect.width + padding);
      const top = Math.max(0, rect.y + rect.height * footprintTopRatio);
      const bottom = Math.min(this.height - 1, rect.y + rect.height + padding);

      const minCell = this.worldToCell(left, top);
      const maxCell = this.worldToCell(right, bottom);

      for (let cy = minCell.cy; cy <= maxCell.cy; cy += 1) {
        for (let cx = minCell.cx; cx <= maxCell.cx; cx += 1) {
          if (!this.inBounds(cx, cy)) {
            continue;
          }

          const center = this.cellToWorldCenter(cx, cy);
          const inRect =
            center.x >= left &&
            center.x <= right &&
            center.y >= top &&
            center.y <= bottom;

          if (inRect) {
            this.walkable[cy][cx] = false;
          }
        }
      }
    }
  }

  drawDebugGrid(ctx, alpha = 0.3) {
    ctx.save();
    ctx.globalAlpha = alpha;
    for (let y = 0; y < this.gridHeight; y += 1) {
      for (let x = 0; x < this.gridWidth; x += 1) {
        if (!this.walkable[y][x]) {
          continue;
        }
        ctx.fillStyle = "#22c55e";
        ctx.fillRect(
          x * this.cellSize,
          y * this.cellSize,
          this.cellSize,
          this.cellSize
        );
      }
    }
    ctx.restore();
  }
}
