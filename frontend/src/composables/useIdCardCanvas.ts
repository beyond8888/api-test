/**
 * 身份证图片生成器 —— 基于 Python 预处理的干净模板直接写文字。
 *
 * 模板 idcard-front-clean.png 已在构建期由 OpenCV inpaint 去除
 * 原姓名值与身份证号数字（标签保留），前端只负责写入新数据。
 * 坐标与字号均来自模板像素分析，写死无需调整。
 * 公共能力（字体/加载/绘制/下载/随机数据）复用 @/utils 下工具。
 */

import {
  FONT_SANS, FONT_MONO, loadImage, createCanvas, fillText,
} from '@/utils/canvasImage'
import { genderFromId, randomNation, randomAddress } from '@/utils/randomData'

// 画布 = 模板原始分辨率，坐标零换算，导出高清
export const CANVAS_W = 1858
export const CANVAS_H = 1184

const FRONT_TPL = '/templates/idcard-front-v8.png?v=3'
const BACK_TPL  = '/templates/idcard-back.png?v=3'

// ─── 写字坐标（模板字符级分析结果，勿改）──────────────────────────
/** 姓名：原值 x 383~522, y 189~264，标签在 x 182~300 */
const NAME = { x: 385, centerY: 228, size: 58 }
/** 性别：原值 x 394~434, y 338~391，标签在 x 180~313 */
const GENDER = { x: 392, centerY: 364, size: 44 }
/** 民族：原值 x 748~790, y 338~391，标签在 x 578~712 */
const NATION = { x: 746, centerY: 364, size: 44 }
/** 住址：标签"住址" x 173~299，原值"北京市..." x 412~1133, y 616~674（y616 行即住址行） */
const ADDRESS = { x: 415, centerY: 645, size: 48 }
/** 出生日期行（y 693~750）：模板自带原生日期，保留原样不写入 */
/** 号码：原值 x 758~1128, y 963~1032，标签"公民身份号码"在 x 157~561 */
const ID_NUM = { x: 655, centerY: 998, size: 58, charStep: 34 }

// ─── 写入文字 ─────────────────────────────────────────────────────
function fillIdNumber(ctx: CanvasRenderingContext2D, idNumber: string): void {
  ctx.font = `bold ${ID_NUM.size}px ${FONT_MONO}`
  ctx.fillStyle = '#1a1a1a'
  ctx.textBaseline = 'middle'
  ctx.textAlign = 'left'
  // 等宽逐字绘制，对齐原数字间距
  let cx = ID_NUM.x
  for (const ch of idNumber) {
    ctx.fillText(ch, cx, ID_NUM.centerY)
    cx += ID_NUM.charStep
  }
}

// ─── 加水印 ────────────────────────────────────────────────────────
function addWatermark(ctx: CanvasRenderingContext2D, w: number, h: number): void {
  ctx.save()

  // 主水印（字号随分辨率放大 2.17 倍）
  ctx.font = `bold 60px ${FONT_SANS}`
  ctx.fillStyle = 'rgba(220,38,38,0.22)'
  ctx.textAlign = 'center'
  ctx.textBaseline = 'middle'

  const diag = Math.sqrt(w * w + h * h)
  const step = 434
  for (let d = -diag; d < diag * 2; d += step) {
    ctx.save()
    ctx.translate(w / 2, h / 2)
    ctx.rotate(-0.45)
    ctx.fillText('测试专用', d, 0)
    ctx.restore()
  }

  // 底部声明
  ctx.font = `24px ${FONT_SANS}`
  ctx.fillStyle = 'rgba(100,100,100,0.5)'
  ctx.textAlign = 'left'
  ctx.textBaseline = 'bottom'
  ctx.fillText('本图片仅供测试使用，不具备任何法律效力', 43, h - 22)

  ctx.restore()
}

// ════════════════════════════════════════════════════════════════════
//  公开 API
// ════════════════════════════════════════════════════════════════════

/**
 * 生成正面：干净模板 + 姓名/性别/民族/住址/号码 + 水印
 * 性别从身份证号第17位推导；出生日期行保留模板原生内容不写入。
 */
export async function generateFront(name: string, idNumber: string): Promise<string> {
  const tpl = await loadImage(FRONT_TPL)
  const { canvas, ctx } = createCanvas(CANVAS_W, CANVAS_H)
  ctx.drawImage(tpl, 0, 0)
  fillText(ctx, name, NAME)
  fillText(ctx, genderFromId(idNumber), GENDER)
  fillText(ctx, randomNation(), NATION)
  fillText(ctx, randomAddress(), ADDRESS)
  fillIdNumber(ctx, idNumber)
  addWatermark(ctx, canvas.width, canvas.height)
  return canvas.toDataURL('image/png')
}

/**
 * 生成反面：与正面同尺寸画布 1858×1184，等比居中绘制反面模板，
 * 保证正反两面输出比例完全一致（一致画布、一致预览、一致下载尺寸）。
 */
export async function generateBack(): Promise<string> {
  const tpl = await loadImage(BACK_TPL)
  const { canvas, ctx } = createCanvas(CANVAS_W, CANVAS_H)
  // 填底色（白色）防止透明背景
  ctx.fillStyle = '#ffffff'
  ctx.fillRect(0, 0, canvas.width, canvas.height)
  // 等比缩放至最大适配，居中绘制
  const tw = tpl.naturalWidth
  const th = tpl.naturalHeight
  const k = Math.min(canvas.width / tw, canvas.height / th)
  const w = tw * k
  const h = th * k
  ctx.drawImage(tpl, (canvas.width - w) / 2, (canvas.height - h) / 2, w, h)
  addWatermark(ctx, canvas.width, canvas.height)
  return canvas.toDataURL('image/png')
}
