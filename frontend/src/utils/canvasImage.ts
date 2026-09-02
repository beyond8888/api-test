/**
 * 画布图片生成公共能力 —— 供所有证件/图片生成器复用。
 *
 * 集中管理：字体常量、模板加载、文字绘制（含旋转/对齐/字重）、画布创建与下载。
 * 各生成器只保留自身的字段坐标与绘制策略，不再重复定义这些基础能力。
 */

/** 中文正文/标题字体（各证件模板均用此字体族） */
export const FONT_SANS =
  "'PingFang SC','Microsoft YaHei','Heiti SC','Noto Sans SC',sans-serif"

/** 等宽数字字体（身份证号、证号、日期等数字字段） */
export const FONT_MONO =
  "'SF Mono','Menlo','Fira Code','Roboto Mono','Courier New',monospace"

/** 车牌/证号类字段字体（与 FONT_SANS 相同，语义更清晰） */
export const FONT_PLATE = FONT_SANS

/** 图片加载失败统一提示 */
const LOAD_ERR = '图片加载失败'

/** 加载图片资源 */
export function loadImage(src: string): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const img = new Image()
    img.onload = () => resolve(img)
    img.onerror = () => reject(new Error(`${LOAD_ERR}: ${src}`))
    img.src = src
  })
}

/** 创建指定尺寸画布，返回 canvas 与 2d 上下文 */
export function createCanvas(w: number, h: number): {
  canvas: HTMLCanvasElement
  ctx: CanvasRenderingContext2D
} {
  const canvas = document.createElement('canvas')
  canvas.width = w
  canvas.height = h
  const ctx = canvas.getContext('2d')
  if (!ctx) throw new Error('无法创建 canvas 2d 上下文')
  return { canvas, ctx }
}

/** 文字位置（含可选的右/中对齐与旋转参数） */
export interface TextPos {
  x: number
  centerY: number
  size: number
  align?: CanvasTextAlign
  /** 顺时针旋转角度（度），用于矫正底图文字倾斜 */
  rotate?: number
  /** 旋转中心，默认取文字起点 (x, centerY) */
  rotateOrigin?: { x: number; y: number }
}

/** 绘制选项 */
export interface FillTextOptions {
  /** 字重，默认 bold（车牌字段传 500 / 400 以匹配模板观感） */
  weight?: number | string
  /** 字体族，默认 FONT_SANS，数字字段传 'mono' */
  font?: 'sans' | 'mono'
  /** 文字颜色，默认 #1a1a1a */
  color?: string
}

/**
 * 统一文字绘制：一次设置字体/颜色/基线，支持对齐与绕任意中心旋转。
 * 各生成器原有的 fillText 行为（bold 正文 / 500 车牌 / 400 证号）均可经
 * weight 参数保持一致，无行为回归。
 */
export function fillText(
  ctx: CanvasRenderingContext2D,
  text: string,
  pos: TextPos,
  opts: FillTextOptions = {},
): void {
  const { weight = 'bold', font = 'sans', color = '#1a1a1a' } = opts
  const family = font === 'mono' ? FONT_MONO : FONT_SANS

  ctx.save()
  ctx.font = `${weight} ${pos.size}px ${family}`
  ctx.fillStyle = color
  ctx.textBaseline = 'middle'
  ctx.textAlign = pos.align || 'left'

  if (pos.rotate) {
    const ox = pos.rotateOrigin?.x ?? pos.x
    const oy = pos.rotateOrigin?.y ?? pos.centerY
    ctx.translate(ox, oy)
    ctx.rotate((pos.rotate * Math.PI) / 180)
    ctx.translate(-ox, -oy)
  }

  ctx.fillText(text, pos.x, pos.centerY)
  ctx.restore()
}

/** 下载图片默认大小上限（3MB） */
export const MAX_IMAGE_BYTES = 3 * 1024 * 1024

/** 计算 dataURL 解码后的实际字节数（base64 长度换算） */
function dataUrlBytes(dataUrl: string): number {
  const base64 = dataUrl.slice(dataUrl.indexOf(',') + 1)
  const padding = base64.endsWith('==') ? 2 : base64.endsWith('=') ? 1 : 0
  return Math.floor((base64.length * 3) / 4) - padding
}

/**
 * 将 dataURL 渐进压缩到指定字节数以内：
 * 先保持原尺寸降低 JPEG 质量，仍超限再等比缩小尺寸，最终必然满足上限。
 * 用于证件类大图（如 1858×1184 身份证）下载时的体积控制。
 */
async function compressDataUrl(src: string, maxBytes: number): Promise<string> {
  const img = await loadImage(src)
  let w = img.naturalWidth
  let h = img.naturalHeight
  let quality = 0.92
  for (;;) {
    const { canvas, ctx } = createCanvas(w, h)
    // 铺白底，防止原图透明区域在 JPEG 编码下变黑
    ctx.fillStyle = '#ffffff'
    ctx.fillRect(0, 0, w, h)
    ctx.drawImage(img, 0, 0, w, h)
    const out = canvas.toDataURL('image/jpeg', quality)
    if (dataUrlBytes(out) <= maxBytes || w <= 640) return out
    if (quality > 0.6) {
      quality -= 0.08
    } else {
      w = Math.round(w * 0.85)
      h = Math.round(h * 0.85)
      quality = 0.85
    }
  }
}

/**
 * 下载图片（dataURL 或 URL）。
 * 生成类图片若超过默认 3MB 上限，会渐进压缩后再下载，保证文件体积可控。
 */
export async function downloadImage(
  url: string,
  filename = 'image.png',
  maxBytes = MAX_IMAGE_BYTES,
): Promise<void> {
  let target = url
  try {
    if (url.startsWith('data:') && dataUrlBytes(url) > maxBytes) {
      target = await compressDataUrl(url, maxBytes)
      // 压缩产物为 JPEG，同步修正文件名后缀
      filename = filename.replace(/\.png$/i, '.jpg')
    }
  } catch {
    // 压缩失败时回退直接下载原图
  }
  const a = document.createElement('a')
  a.href = target
  a.download = filename
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
}
