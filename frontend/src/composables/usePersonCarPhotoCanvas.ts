import { ref, watch } from 'vue'
import { downloadImage } from '@/utils/canvasImage'

export interface PlateOptions {
  number: string
}

// 固定车牌绘制区（模板坐标系 1080×720），中心与旧字位置 (609, 627.5) 对齐
const PLATE_RECT = { x: 525, y: 598, w: 168, h: 59 }
// 字号整体调小（旧字框高 35 的约 0.86 倍），视觉更贴合车头
const CHAR_H = 30
const CN_Y_OFFSET = 3

const NUM_SIZE_RATIO = 0.95
const SPACING_RATIO = 0.08

const FONT_STACK = '"STHeiti Medium", "STHeiti", "PingFang SC", "Microsoft YaHei", "Heiti SC", sans-serif'

export function usePersonCarPhotoCanvas() {
  const canvas = ref<HTMLCanvasElement | null>(null)
  const image = ref<HTMLImageElement | null>(null)
  const loading = ref(false)
  const error = ref('')
  const options = ref<PlateOptions>({ number: '' })

  function loadTemplate(src: string) {
    return new Promise<void>((resolve, reject) => {
      loading.value = true
      error.value = ''
      const img = new Image()
      img.onload = () => {
        image.value = img
        if (canvas.value) {
          canvas.value.width = img.naturalWidth
          canvas.value.height = img.naturalHeight
        }
        loading.value = false
        requestAnimationFrame(() => {
          try {
            draw()
          } catch (e) {
            error.value = '绘制失败: ' + (e as Error).message
          }
          resolve()
        })
      }
      img.onerror = () => {
        loading.value = false
        error.value = '模板图加载失败'
        reject(new Error(error.value))
      }
      img.src = src
    })
  }

  interface CharMetric { char: string; size: number; width: number; isCn: boolean }

  function measureChars(ctx: CanvasRenderingContext2D, text: string): CharMetric[] {
    const cnSize = CHAR_H
    const numSize = Math.round(cnSize * NUM_SIZE_RATIO)
    return [...text].map((char) => {
      const isCn = !/[0-9A-Z]/.test(char)
      const size = isCn ? cnSize : numSize
      ctx.font = `bold ${size}px ${FONT_STACK}`
      const m = ctx.measureText(char)
      const width = (m.actualBoundingBoxLeft !== undefined)
        ? (m.actualBoundingBoxLeft + m.actualBoundingBoxRight) || m.width
        : m.width
      return { char, size, width, isCn }
    })
  }

  function drawPlateText(ctx: CanvasRenderingContext2D, text: string) {
    const { x, y, w, h } = PLATE_RECT
    const spacing = Math.max(2, Math.round(CHAR_H * SPACING_RATIO))
    const metrics = measureChars(ctx, text)
    const totalW = metrics.reduce((s, m) => s + m.width, 0) + spacing * (metrics.length - 1)

    const usableW = w - w * 0.08
    const scale = totalW > usableW ? usableW / totalW : 1
    const cy = y + h / 2
    let cur = x + (w - totalW * scale) / 2

    ctx.textAlign = 'center'
    ctx.textBaseline = 'middle'
    for (const m of metrics) {
      const size = m.size * scale
      ctx.font = `bold ${size.toFixed(1)}px ${FONT_STACK}`
      const centerX = cur + (m.width * scale) / 2
      const yc = cy - (m.isCn ? CN_Y_OFFSET : 0)
      ctx.fillStyle = 'rgba(0, 0, 0, 0.28)'
      ctx.fillText(m.char, centerX + 1, yc + 1)
      ctx.fillStyle = '#ffffff'
      ctx.fillText(m.char, centerX, yc)
      cur += m.width * scale + spacing * scale
    }
  }

  function draw() {
    const cvs = canvas.value
    const img = image.value
    if (!cvs || !img) return

    const ctx = cvs.getContext('2d')
    if (!ctx) return

    ctx.clearRect(0, 0, cvs.width, cvs.height)
    ctx.drawImage(img, 0, 0, cvs.width, cvs.height)

    const { number } = options.value
    if (!number) return

    drawPlateText(ctx, number)
  }

  function download(filename?: string) {
    const cvs = canvas.value
    if (!cvs) return
    downloadImage(cvs.toDataURL('image/png'), filename || `人车合影-${options.value.number || 'preview'}.png`)
  }

  watch(() => ({ ...options.value }), draw, { deep: true })

  // 组件可能晚于模板加载才挂载 canvas（如结果区 v-if 渲染），挂载时补齐尺寸并重绘
  watch(canvas, (cvs) => {
    if (!cvs || !image.value) return
    cvs.width = image.value.naturalWidth
    cvs.height = image.value.naturalHeight
    draw()
  })

  return {
    canvas,
    image,
    loading,
    error,
    options,
    loadTemplate,
    draw,
    download,
  }
}