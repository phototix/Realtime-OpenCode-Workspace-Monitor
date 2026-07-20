export class CharacterAnimator {
  constructor(spriteSheet, options = {}) {
    this.spriteSheet = this.prepareSheet(spriteSheet, options);
    this.columns = options.columns ?? 7;
    this.rows = options.rows ?? 1;
    this.fps = options.fps ?? 12;
    this.sequenceIsGridIndex = options.sequenceIsGridIndex ?? false;
    this.sheetScale = options.sheetScale ?? 1;

    this.directionRows = options.directionRows ?? {
      right: 0,
      "down-right": 0,
      down: 0,
      "down-left": 0,
      left: 0,
      "up-left": 0,
      up: 0,
      "up-right": 0,
    };

    this.frameSequence =
      options.frameSequence ??
      (this.columns > 2
        ? [
            ...Array.from({ length: this.columns }, (_, i) => i),
            ...Array.from({ length: this.columns - 2 }, (_, i) => this.columns - 2 - i),
          ]
        : Array.from({ length: this.columns }, (_, i) => i));

    this.frameAnchors = this.computeFrameAnchors();

    this.frameTimer = 0;
    this.frameCursor = 0;
    this.isMoving = false;

    this.direction = "down";
    this.profile = this.getProfile(this.direction);
  }

  setDirection(direction) {
    if (direction === this.direction) {
      return;
    }
    this.direction = direction;
    this.profile = this.getProfile(direction);
  }

  setMoving(moving) {
    this.isMoving = moving;
    if (!moving) {
      this.frameCursor = 0;
      this.frameTimer = 0;
    }
  }

  update(dt) {
    if (!this.isMoving) {
      return;
    }

    this.frameTimer += dt;
    const frameDuration = 1 / this.fps;
    while (this.frameTimer >= frameDuration) {
      this.frameTimer -= frameDuration;
      this.frameCursor = (this.frameCursor + 1) % this.frameSequence.length;
    }
  }

  draw(ctx, x, y, scale = 1.0) {
    const frameRef = this.resolveFrameRef(this.frameSequence[this.frameCursor] ?? 0);
    const row = frameRef.row;
    const col = frameRef.col;

    const cell = this.cellRect(col, row);
    const sx = cell.x;
    const sy = cell.y;
    const sw = cell.width;
    const sh = cell.height;

    const drawScale = scale * this.sheetScale;
    const destW = sw * drawScale;
    const destH = sh * drawScale;
    const anchor = this.frameAnchors[row]?.[col] ?? {
      footX: sw * 0.5,
      footY: sh * 0.92,
    };

    // Position uses feet anchor for better floor contact.
    const drawX = x - anchor.footX * drawScale;
    const drawY = y - anchor.footY * drawScale;

    ctx.save();
    ctx.imageSmoothingEnabled = false;

    ctx.drawImage(
      this.spriteSheet,
      sx,
      sy,
      sw,
      sh,
      drawX,
      drawY,
      destW,
      destH
    );
    ctx.restore();
  }

  getProfile(direction) {
    return {
      row: this.directionRows[direction] ?? this.directionRows.down ?? 0,
    };
  }

  resolveFrameRef(frameRef) {
    if (typeof frameRef === "object" && frameRef !== null) {
      return {
        col: frameRef.col ?? 0,
        row: frameRef.row ?? this.profile.row,
      };
    }

    if (this.sequenceIsGridIndex) {
      const index = Math.max(0, Number(frameRef) || 0);
      return {
        col: index % this.columns,
        row: Math.floor(index / this.columns) % this.rows,
      };
    }

    return {
      col: Number(frameRef) || 0,
      row: this.profile.row,
    };
  }

  prepareSheet(sheet, options) {
    const columns = options.columns ?? 6;
    const rows = options.rows ?? 8;
    const keyThreshold = options.keyThreshold ?? 42;
    const cleanupIslands = options.cleanupIslands ?? true;
    const minIslandArea = options.minIslandArea ?? 20;

    const canvas = document.createElement("canvas");
    canvas.width = sheet.width;
    canvas.height = sheet.height;
    const ctx = canvas.getContext("2d", { willReadFrequently: true });
    ctx.drawImage(sheet, 0, 0);

    const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
    const data = imageData.data;

    if (options.colorKeyBlack) {
      const samplePixel = (x, y) => {
        const i = (y * canvas.width + x) * 4;
        return [data[i], data[i + 1], data[i + 2]];
      };

      for (let row = 0; row < rows; row += 1) {
        const y0 = Math.round((row * canvas.height) / rows);
        const y1 = Math.round(((row + 1) * canvas.height) / rows);
        const h = Math.max(1, y1 - y0);

        for (let col = 0; col < columns; col += 1) {
          const x0 = Math.round((col * canvas.width) / columns);
          const x1 = Math.round(((col + 1) * canvas.width) / columns);
          const w = Math.max(1, x1 - x0);

          const corners = [
            samplePixel(x0, y0),
            samplePixel(x1 - 1, y0),
            samplePixel(x0, y1 - 1),
            samplePixel(x1 - 1, y1 - 1),
          ];

          const bg = corners
            .reduce(
              (acc, c) => [acc[0] + c[0], acc[1] + c[1], acc[2] + c[2]],
              [0, 0, 0]
            )
            .map((v) => v / corners.length);

          for (let y = 0; y < h; y += 1) {
            for (let x = 0; x < w; x += 1) {
              const gx = x0 + x;
              const gy = y0 + y;
              const i = (gy * canvas.width + gx) * 4;
              const dr = Math.abs(data[i] - bg[0]);
              const dg = Math.abs(data[i + 1] - bg[1]);
              const db = Math.abs(data[i + 2] - bg[2]);
              const d = dr + dg + db;

              if (d <= keyThreshold) {
                data[i + 3] = 0;
              }
            }
          }
        }
      }
    }

    if (cleanupIslands) {
      for (let row = 0; row < rows; row += 1) {
        const y0 = Math.round((row * canvas.height) / rows);
        const y1 = Math.round(((row + 1) * canvas.height) / rows);
        const h = Math.max(1, y1 - y0);

        for (let col = 0; col < columns; col += 1) {
          const x0 = Math.round((col * canvas.width) / columns);
          const x1 = Math.round(((col + 1) * canvas.width) / columns);
          const w = Math.max(1, x1 - x0);

          const visited = new Uint8Array(w * h);
          const components = [];
          const key = (x, y) => y * w + x;

          const alphaAt = (x, y) => {
            const gx = x0 + x;
            const gy = y0 + y;
            return data[(gy * canvas.width + gx) * 4 + 3];
          };

          for (let y = 0; y < h; y += 1) {
            for (let x = 0; x < w; x += 1) {
              const id = key(x, y);
              if (visited[id] || alphaAt(x, y) < 20) {
                continue;
              }

              const queue = [[x, y]];
              visited[id] = 1;
              let head = 0;
              let area = 0;
              const pixels = [];

              while (head < queue.length) {
                const [px, py] = queue[head++];
                area += 1;
                pixels.push([px, py]);
                for (let oy = -1; oy <= 1; oy += 1) {
                  for (let ox = -1; ox <= 1; ox += 1) {
                    if (ox === 0 && oy === 0) {
                      continue;
                    }
                    const nx = px + ox;
                    const ny = py + oy;
                    if (nx < 0 || ny < 0 || nx >= w || ny >= h) {
                      continue;
                    }
                    const nid = key(nx, ny);
                    if (visited[nid] || alphaAt(nx, ny) < 20) {
                      continue;
                    }
                    visited[nid] = 1;
                    queue.push([nx, ny]);
                  }
                }
              }

              components.push({ area, pixels });
            }
          }

          if (components.length <= 1) {
            continue;
          }

          const maxArea = Math.max(...components.map((c) => c.area));
          for (const comp of components) {
            if (comp.area >= Math.max(minIslandArea, maxArea * 0.08)) {
              continue;
            }
            for (const [px, py] of comp.pixels) {
              const gx = x0 + px;
              const gy = y0 + py;
              data[(gy * canvas.width + gx) * 4 + 3] = 0;
            }
          }
        }
      }
    }

    ctx.putImageData(imageData, 0, 0);
    return canvas;
  }

  cellStartX(col) {
    return Math.round((col * this.spriteSheet.width) / this.columns);
  }

  cellStartY(row) {
    return Math.round((row * this.spriteSheet.height) / this.rows);
  }

  cellRect(col, row) {
    const x0 = this.cellStartX(col);
    const x1 = Math.round(((col + 1) * this.spriteSheet.width) / this.columns);
    const y0 = this.cellStartY(row);
    const y1 = Math.round(((row + 1) * this.spriteSheet.height) / this.rows);
    return {
      x: x0,
      y: y0,
      width: Math.max(1, x1 - x0),
      height: Math.max(1, y1 - y0),
    };
  }

  computeFrameAnchors() {
    const scan = document.createElement("canvas");
    scan.width = this.spriteSheet.width;
    scan.height = this.spriteSheet.height;
    const scanCtx = scan.getContext("2d", { willReadFrequently: true });
    scanCtx.drawImage(this.spriteSheet, 0, 0);
    const data = scanCtx.getImageData(0, 0, scan.width, scan.height).data;

    const out = Array.from({ length: this.rows }, () =>
      Array.from({ length: this.columns }, () => ({ footX: 0, footY: 0 }))
    );

    for (let row = 0; row < this.rows; row += 1) {
      for (let col = 0; col < this.columns; col += 1) {
        const cell = this.cellRect(col, row);
        const cellX = cell.x;
        const cellY = cell.y;

        let footY = Math.floor(cell.height * 0.92);
        let foundFoot = false;
        for (let y = cell.height - 1; y >= 0 && !foundFoot; y -= 1) {
          for (let x = 0; x < cell.width; x += 1) {
            const sx = cellX + x;
            const sy = cellY + y;
            const i = (sy * scan.width + sx) * 4;
            if (data[i + 3] >= 20) {
              footY = y;
              foundFoot = true;
              break;
            }
          }
        }

        let weightedX = 0;
        let weightSum = 0;

        // Sample a thin band around the foot line for stable horizontal anchoring.
        for (let y = Math.max(0, footY - 2); y <= Math.min(cell.height - 1, footY + 1); y += 1) {
          for (let x = 0; x < cell.width; x += 1) {
            const sx = cellX + x;
            const sy = cellY + y;
            const i = (sy * scan.width + sx) * 4;
            const a = data[i + 3];
            if (a < 20) {
              continue;
            }

            const weight = a;
            weightedX += x * weight;
            weightSum += weight;
          }
        }

        const footX = weightSum > 0 ? weightedX / weightSum : cell.width * 0.5;
        out[row][col] = { footX, footY };
      }
    }

    return out;
  }
}
