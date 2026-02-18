/**
 * Downsample an array to at most `maxPoints` entries.
 * Uses uniform interval sampling, always keeping first and last points.
 */
export function downsample<T>(data: T[], maxPoints = 1000): T[] {
  if (data.length <= maxPoints) return data;
  const step = (data.length - 1) / (maxPoints - 1);
  const result: T[] = [];
  for (let i = 0; i < maxPoints - 1; i++) {
    result.push(data[Math.round(i * step)]);
  }
  result.push(data[data.length - 1]);
  return result;
}
