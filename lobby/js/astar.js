export class AStar {
  static findPath(map, start, goal, allowDiagonal = true) {
    if (!start || !goal) {
      return [];
    }
    if (!map.isWalkableCell(goal.cx, goal.cy)) {
      return [];
    }

    const key = (x, y) => `${x},${y}`;
    const decode = (k) => {
      const [x, y] = k.split(",").map(Number);
      return { cx: x, cy: y };
    };

    const open = new Set([key(start.cx, start.cy)]);
    const cameFrom = new Map();

    const g = new Map([[key(start.cx, start.cy), 0]]);
    const f = new Map([
      [key(start.cx, start.cy), this.heuristic(start.cx, start.cy, goal.cx, goal.cy)],
    ]);

    while (open.size > 0) {
      let currentKey = null;
      let best = Number.POSITIVE_INFINITY;
      for (const candidate of open) {
        const score = f.get(candidate) ?? Number.POSITIVE_INFINITY;
        if (score < best) {
          best = score;
          currentKey = candidate;
        }
      }

      if (!currentKey) {
        break;
      }

      const current = decode(currentKey);
      if (current.cx === goal.cx && current.cy === goal.cy) {
        return this.reconstructPath(cameFrom, currentKey).map(decode);
      }

      open.delete(currentKey);

      for (const [nx, ny, moveCost] of this.getNeighbors(map, current, allowDiagonal)) {
        const nKey = key(nx, ny);
        const tentativeG = (g.get(currentKey) ?? Number.POSITIVE_INFINITY) + moveCost;

        if (tentativeG >= (g.get(nKey) ?? Number.POSITIVE_INFINITY)) {
          continue;
        }

        cameFrom.set(nKey, currentKey);
        g.set(nKey, tentativeG);
        f.set(nKey, tentativeG + this.heuristic(nx, ny, goal.cx, goal.cy));
        open.add(nKey);
      }
    }

    return [];
  }

  static getNeighbors(map, current, allowDiagonal) {
    const dirs4 = [
      [1, 0],
      [-1, 0],
      [0, 1],
      [0, -1],
    ];
    const dirsDiag = [
      [1, 1],
      [1, -1],
      [-1, 1],
      [-1, -1],
    ];

    const out = [];

    for (const [dx, dy] of dirs4) {
      const nx = current.cx + dx;
      const ny = current.cy + dy;
      if (map.isWalkableCell(nx, ny)) {
        out.push([nx, ny, 1]);
      }
    }

    if (allowDiagonal) {
      for (const [dx, dy] of dirsDiag) {
        const nx = current.cx + dx;
        const ny = current.cy + dy;
        if (!map.isWalkableCell(nx, ny)) {
          continue;
        }

        // Prevent corner cutting through obstacles.
        if (!map.isWalkableCell(current.cx + dx, current.cy)) {
          continue;
        }
        if (!map.isWalkableCell(current.cx, current.cy + dy)) {
          continue;
        }

        out.push([nx, ny, Math.SQRT2]);
      }
    }

    return out;
  }

  static heuristic(x1, y1, x2, y2) {
    // Octile distance works well for 8-direction movement.
    const dx = Math.abs(x1 - x2);
    const dy = Math.abs(y1 - y2);
    return (dx + dy) + (Math.SQRT2 - 2) * Math.min(dx, dy);
  }

  static reconstructPath(cameFrom, currentKey) {
    const path = [currentKey];
    let current = currentKey;
    while (cameFrom.has(current)) {
      current = cameFrom.get(current);
      path.push(current);
    }
    path.reverse();
    return path;
  }
}
