function createCanvas(width, height) {
  const canvas = document.createElement("canvas");
  canvas.width = width;
  canvas.height = height;
  return canvas;
}

function getImageData(source) {
  const canvas = createCanvas(source.width, source.height);
  const ctx = canvas.getContext("2d", { willReadFrequently: true });
  ctx.drawImage(source, 0, 0);
  return ctx.getImageData(0, 0, canvas.width, canvas.height);
}

function extractConnectedComponentsFromMask(width, height, isForeground, minPixels = 120) {
  const visited = new Uint8Array(width * height);
  const qx = new Int32Array(width * height);
  const qy = new Int32Array(width * height);
  const components = [];

  for (let y = 0; y < height; y += 1) {
    for (let x = 0; x < width; x += 1) {
      const rootIdx = y * width + x;
      if (visited[rootIdx] || !isForeground(x, y)) {
        continue;
      }

      let minX = x;
      let minY = y;
      let maxX = x;
      let maxY = y;
      let count = 0;

      let head = 0;
      let tail = 0;
      qx[tail] = x;
      qy[tail] = y;
      tail += 1;
      visited[rootIdx] = 1;

      while (head < tail) {
        const px = qx[head];
        const py = qy[head];
        head += 1;
        count += 1;

        if (px < minX) minX = px;
        if (py < minY) minY = py;
        if (px > maxX) maxX = px;
        if (py > maxY) maxY = py;

        for (let oy = -1; oy <= 1; oy += 1) {
          for (let ox = -1; ox <= 1; ox += 1) {
            if (ox === 0 && oy === 0) continue;
            const nx = px + ox;
            const ny = py + oy;

            if (nx < 0 || ny < 0 || nx >= width || ny >= height) {
              continue;
            }

            const nIdx = ny * width + nx;
            if (visited[nIdx] || !isForeground(nx, ny)) {
              continue;
            }

            visited[nIdx] = 1;
            qx[tail] = nx;
            qy[tail] = ny;
            tail += 1;
          }
        }
      }

      if (count >= minPixels) {
        components.push({
          minX,
          minY,
          maxX,
          maxY,
          width: maxX - minX + 1,
          height: maxY - minY + 1,
          area: count,
        });
      }
    }
  }

  return components;
}

function analyzeAssetSheet(assetsSheetImage) {
  const imageData = getImageData(assetsSheetImage);
  const { data, width, height } = imageData;

  const isForeground = (x, y) => {
    const i = (y * width + x) * 4;
    const a = data[i + 3];
    if (a < 10) {
      return false;
    }

    const r = data[i];
    const g = data[i + 1];
    const b = data[i + 2];

    return !(r > 245 && g > 245 && b > 245);
  };

  const assets = extractConnectedComponentsFromMask(width, height, isForeground, 220);
  return { extractedAssets: assets.length };
}

function buildSceneDiffMask(refImageData, emptyImageData, threshold) {
  const { width, height } = refImageData;
  const ref = refImageData.data;
  const empty = emptyImageData.data;
  const mask = new Uint8Array(width * height);

  for (let y = 0; y < height; y += 1) {
    for (let x = 0; x < width; x += 1) {
      const i = (y * width + x) * 4;
      const diff =
        Math.abs(ref[i] - empty[i]) +
        Math.abs(ref[i + 1] - empty[i + 1]) +
        Math.abs(ref[i + 2] - empty[i + 2]);

      if (diff > threshold) {
        mask[y * width + x] = 1;
      }
    }
  }

  return mask;
}

function pickBestThreshold(refImageData, emptyImageData) {
  const thresholds = [100, 120, 140, 160, 180];
  const targetComponents = 22;

  let best = {
    threshold: thresholds[0],
    score: Number.POSITIVE_INFINITY,
    components: [],
    mask: null,
  };

  for (const threshold of thresholds) {
    const mask = buildSceneDiffMask(refImageData, emptyImageData, threshold);
    const components = extractConnectedComponentsFromMask(
      refImageData.width,
      refImageData.height,
      (x, y) => mask[y * refImageData.width + x] === 1,
      140
    );

    const huge = components.filter((c) => c.area > 50000).length;
    const tiny = components.filter((c) => c.area < 500).length;
    const score =
      Math.abs(components.length - targetComponents) +
      huge * 3 +
      tiny * 0.2;

    if (score < best.score) {
      best = {
        threshold,
        score,
        components,
        mask,
      };
    }
  }

  return best;
}

function makeComponentSprite(
  officeReferenceImage,
  renderMask,
  sceneWidth,
  sceneHeight,
  component,
  useMask = true
) {
  const sprite = createCanvas(component.width, component.height);
  const ctx = sprite.getContext("2d", { willReadFrequently: true });
  ctx.drawImage(
    officeReferenceImage,
    component.minX,
    component.minY,
    component.width,
    component.height,
    0,
    0,
    component.width,
    component.height
  );

  if (!useMask) {
    return sprite;
  }

  const imageData = ctx.getImageData(0, 0, component.width, component.height);
  const data = imageData.data;

  for (let y = 0; y < component.height; y += 1) {
    for (let x = 0; x < component.width; x += 1) {
      const worldX = component.minX + x;
      const worldY = component.minY + y;
      const worldIdx = worldY * sceneWidth + worldX;

      // Keep pixel if it belongs to object mask or near object mask (edge anti-alias support).
      let keep = renderMask[worldIdx] === 1;
      if (!keep) {
        for (let oy = -1; oy <= 1 && !keep; oy += 1) {
          for (let ox = -1; ox <= 1; ox += 1) {
            const nx = worldX + ox;
            const ny = worldY + oy;
            if (nx < 0 || ny < 0 || nx >= sceneWidth || ny >= sceneHeight) {
              continue;
            }
            const nIdx = ny * sceneWidth + nx;
            if (renderMask[nIdx] === 1) {
              keep = true;
              break;
            }
          }
        }
      }

      if (keep) {
        continue;
      }

      const i = (y * component.width + x) * 4;
      data[i + 3] = 0;
    }
  }

  ctx.putImageData(imageData, 0, 0);
  return sprite;
}

function classifyComponent(component, renderMask, sceneWidth) {
  const aspect = component.width / Math.max(1, component.height);
  const bandHeight = Math.max(1, Math.floor(component.height * 0.22));
  const yStart = component.maxY - bandHeight + 1;

  let bottomOnMask = 0;
  let bottomTotal = 0;

  for (let y = yStart; y <= component.maxY; y += 1) {
    for (let x = component.minX; x <= component.maxX; x += 1) {
      bottomTotal += 1;
      if (renderMask[y * sceneWidth + x] === 1) {
        bottomOnMask += 1;
      }
    }
  }

  const bottomCoverage = bottomOnMask / Math.max(1, bottomTotal);

  // Flat floor-ish patches (rugs/ground decals) should stay behind the character.
  const flatSurfaceLike =
    component.width >= 120 &&
    component.height <= 210 &&
    aspect >= 1.15 &&
    bottomCoverage >= 0.50;

  // Wide low-profile furniture (desks/tables/counters) should not be front occluders,
  // otherwise they slice through the character torso due coarse component grouping.
  const furnitureSurfaceLike =
    component.width >= 150 &&
    component.height <= 190 &&
    aspect >= 1.35;

  if (flatSurfaceLike) {
    return {
      occluder: false,
      blocksPath: false,
    };
  }

  if (furnitureSurfaceLike) {
    return {
      occluder: false,
      blocksPath: false,
    };
  }

  return {
    occluder: component.area < 26000,
    blocksPath: true,
  };
}

export function buildSceneLayers({ officeEmptyImage, assetsSheetImage, officeReferenceImage }) {
  const assetStats = analyzeAssetSheet(assetsSheetImage);

  const refImageData = getImageData(officeReferenceImage);
  const emptyImageData = getImageData(officeEmptyImage);

  const thresholdResult = pickBestThreshold(refImageData, emptyImageData);
  const diffMask = thresholdResult.mask;
  const renderMask = buildSceneDiffMask(refImageData, emptyImageData, 60);
  const components = thresholdResult.components;

  const staticAssets = components.map((component, index) => {
    const classification = classifyComponent(component, renderMask, refImageData.width);
    const occluder = classification.occluder;
    return {
      id: index,
      sprite: makeComponentSprite(
        officeReferenceImage,
        renderMask,
        refImageData.width,
        refImageData.height,
        component,
        occluder
      ),
      x: component.minX,
      y: component.minY,
      width: component.width,
      height: component.height,
      baseY: component.maxY,
      score: component.area,
      occluder,
      blocksPath: classification.blocksPath,
    };
  });

  const pathBlockers = staticAssets
    .filter((asset) => asset.blocksPath)
    .map((asset) => ({
      x: asset.x,
      y: asset.y,
      width: asset.width,
      height: asset.height,
    }));

  staticAssets.sort((a, b) => a.baseY - b.baseY);

  const compositeCanvas = createCanvas(officeEmptyImage.width, officeEmptyImage.height);
  const compositeCtx = compositeCanvas.getContext("2d");
  compositeCtx.drawImage(officeEmptyImage, 0, 0);
  for (const asset of staticAssets) {
    compositeCtx.drawImage(asset.sprite, asset.x, asset.y, asset.width, asset.height);
  }

  return {
    staticAssets,
    pathBlockers,
    compositeCanvas,
    stats: {
      extractedAssets: assetStats.extractedAssets,
      placedAssets: staticAssets.length,
      threshold: thresholdResult.threshold,
      averageMatchScore:
        staticAssets.reduce((sum, asset) => sum + asset.score, 0) /
        Math.max(1, staticAssets.length),
    },
  };
}
