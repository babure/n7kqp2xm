/** Compact MW tick labels — never append units (units live on the axis title). */
export function formatMwTick(value: number): string {
  const v = Number(value)
  if (!Number.isFinite(v)) return ''
  const abs = Math.abs(v)
  if (abs >= 1000) {
    const k = v / 1000
    return Number.isInteger(k) ? `${k}k` : `${k.toFixed(1)}k`
  }
  return `${Math.round(v)}`
}

/**
 * Domain with headroom so the top tick sits below the SVG edge
 * (Recharts centers tick text on the axis, which otherwise clips).
 */
export function yDomainWithHeadroom(
  values: Array<number | null | undefined>,
  opts: { floorZero?: boolean; headroom?: number } = {},
): [number, number] {
  const { floorZero = true, headroom = 0.14 } = opts
  const nums = values.filter((v): v is number => v != null && Number.isFinite(v))
  if (!nums.length) return [0, 1]

  let min = Math.min(...nums)
  let max = Math.max(...nums)
  if (floorZero) min = Math.min(0, min)
  if (max === min) max = min + 1

  const span = max - min
  const top = max + span * headroom
  return [min, niceCeil(top)]
}

function niceCeil(n: number): number {
  if (n <= 0) return 1
  const magnitude = 10 ** Math.floor(Math.log10(n))
  const step = magnitude / 2
  return Math.ceil(n / step) * step
}

/** Room for top legend; axis titles live outside SVG in ChartFrame */
export const chartMargin = {
  desktop: { top: 32, right: 12, left: 4, bottom: 8 },
  narrow: { top: 32, right: 6, left: 0, bottom: 4 },
} as const
