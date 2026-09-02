/**
 * 机动车行驶证图片生成器 —— 替换号牌号码、VIN、发动机号码。
 *
 * 模板 vehicle-license-clean.png 已去除原号牌号码、车辆识别代号（VIN）
 * 与发动机号码，前端负责写入新值。
 * 公共能力（字体/加载/绘制/下载/随机数据）复用 @/utils 下工具。
 */

import { FONT_PLATE, loadImage, fillText } from '@/utils/canvasImage'
import { randomPlateNo, randomVIN, randomEngineNo } from '@/utils/randomData'

const SRC = '/templates/vehicle-license-clean.png?v=3'
const W = 1080
const H = 773

// 写字坐标（基于 青JZ373R-行驶证.png 1080×773 实测标定）
// 号牌实测：青 x232~278、字母 x280~435（总 x234~435），y161~206，中心 y≈184
// size=36、weight=500：青字宽≈36、字母高≈24，与行驶证字段字号匹配
const PLATE = { x: 234, centerY: 184, size: 36 }

// VIN（车辆识别代号）实测：值 x505~904（17 字符）、y500~529，中心 y≈514.5
// 字符中心间距≈23.5px、字高≈29px（size=35 匹配），逐字符绘制保证对齐
const VIN = { x: 505, centerY: 514.5, size: 35, step: 23.5 }

// 发动机号码实测：值 x509~791（12 位示例"444176961362"）、y569~596，中心 y≈582.5
// 一次连续绘制 + size=38（匹配原图字高 27px），字符紧凑自然（非逐字排布）
const ENGINE = { x: 509, centerY: 582.5, size: 38 }

/** VIN 逐字符绘制：按实测中心间距 23.5px 排布，保证 17 位对齐 */
function fillVIN(
  ctx: CanvasRenderingContext2D,
  text: string,
  pos: { x: number; centerY: number; size: number; step: number },
): void {
  ctx.font = `400 ${pos.size}px ${FONT_PLATE}`
  ctx.fillStyle = '#1a1a1a'
  ctx.textBaseline = 'middle'
  ctx.textAlign = 'center'
  Array.from(text).forEach((ch, i) => {
    ctx.fillText(ch, pos.x + pos.step * i + pos.step / 2, pos.centerY)
  })
}

export interface VehicleLicenseResult {
  url: string
}

/**
 * 生成行驶证图片：写入车牌号、VIN（可选）与发动机号码（可选）。
 */
export async function generateVehicleLicense(
  plateNo: string,
  vin?: string,
  engineNo?: string,
): Promise<VehicleLicenseResult> {
  const tpl = await loadImage(SRC)
  const canvas = document.createElement('canvas')
  canvas.width = W
  canvas.height = H
  const ctx = canvas.getContext('2d')!
  ctx.drawImage(tpl, 0, 0)
  // 行驶证车牌/证号字号 weight=500 匹配模板观感（非加粗）
  fillText(ctx, plateNo, PLATE, { weight: 500 })
  if (vin) fillVIN(ctx, vin, VIN)
  if (engineNo) fillText(ctx, engineNo, ENGINE, { weight: 500 })
  return { url: canvas.toDataURL('image/png') }
}
