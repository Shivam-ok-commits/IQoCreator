export interface DominantColors {
  colors: string[];
  error: boolean;
}

function rgbToHex(r: number, g: number, b: number): string {
  const toHex = (n: number) =>
    Math.max(0, Math.min(255, Math.round(n)))
      .toString(16)
      .padStart(2, "0");
  return `#${toHex(r)}${toHex(g)}${toHex(b)}`;
}

function distance(a: number[], b: number[]): number {
  return Math.sqrt(
    (a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2 + (a[2] - b[2]) ** 2,
  );
}

function quantize(pixels: number[][], maxColors: number): number[][] {
  if (pixels.length <= maxColors) return pixels;

  const clusters: { centroid: number[]; count: number }[] = [];
  for (let i = 0; i < maxColors; i++) {
    clusters.push({
      centroid: [...pixels[i % pixels.length]],
      count: 0,
    });
  }

  for (let iter = 0; iter < 5; iter++) {
    const assignments: number[][] = Array.from({ length: maxColors }, () => []);
    for (const p of pixels) {
      let minDist = Infinity;
      let bestIdx = 0;
      for (let i = 0; i < clusters.length; i++) {
        const d = distance(p, clusters[i].centroid);
        if (d < minDist) {
          minDist = d;
          bestIdx = i;
        }
      }
      assignments[bestIdx].push(p[0], p[1], p[2]);
    }

    for (let i = 0; i < clusters.length; i++) {
      const assigned = assignments[i];
      if (assigned.length === 0) continue;
      let r = 0, g = 0, b = 0;
      for (let j = 0; j < assigned.length; j += 3) {
        r += assigned[j];
        g += assigned[j + 1];
        b += assigned[j + 2];
      }
      const count = assigned.length / 3;
      clusters[i] = {
        centroid: [r / count, g / count, b / count],
        count,
      };
    }
  }

  clusters.sort((a, b) => b.count - a.count);
  return clusters.map((c) => c.centroid);
}

function extractFromCanvas(
  image: HTMLImageElement,
  sampleRate: number,
): number[][] {
  const canvas = document.createElement("canvas");
  const ctx = canvas.getContext("2d");
  if (!ctx) return [];

  const maxDim = 64;
  const scale = Math.min(maxDim / image.naturalWidth, maxDim / image.naturalHeight, 1);
  const w = Math.max(1, Math.round(image.naturalWidth * scale));
  const h = Math.max(1, Math.round(image.naturalHeight * scale));
  canvas.width = w;
  canvas.height = h;

  ctx.drawImage(image, 0, 0, w, h);
  const data = ctx.getImageData(0, 0, w, h).data;

  const pixels: number[][] = [];
  for (let i = 0; i < data.length; i += 4 * sampleRate) {
    const r = data[i];
    const g = data[i + 1];
    const b = data[i + 2];
    const a = data[i + 3];
    if (a < 128) continue;
    const lum = 0.2126 * r + 0.7152 * g + 0.0722 * b;
    if (lum < 15 || lum > 240) continue;
    pixels.push([r, g, b]);
  }

  return pixels;
}

export async function extractDominantColors(
  imageUrl: string,
  sampleRate = 2,
  maxColors = 6,
): Promise<DominantColors> {
  return new Promise((resolve) => {
    const img = new Image();
    img.crossOrigin = "anonymous";
    img.referrerPolicy = "no-referrer";

    const timeout = setTimeout(() => {
      img.src = "";
      resolve({ colors: [], error: true });
    }, 10000);

    img.onload = () => {
      clearTimeout(timeout);
      try {
        const pixels = extractFromCanvas(img, sampleRate);
        if (pixels.length === 0) {
          resolve({ colors: [], error: true });
          return;
        }
        const centroids = quantize(pixels, maxColors);
        const colors = centroids.map((c) => rgbToHex(c[0], c[1], c[2]));
        resolve({ colors, error: false });
      } catch {
        resolve({ colors: [], error: true });
      }
    };

    img.onerror = () => {
      clearTimeout(timeout);
      resolve({ colors: [], error: true });
    };

    img.src = imageUrl;
  });
}
