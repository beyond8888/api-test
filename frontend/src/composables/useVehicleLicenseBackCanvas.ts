/**
 * 机动车行驶证副页图片生成器 —— 替换号牌号码、档案编号与检验有效期至日期。
 *
 * 模板 vehicle-license-back-clean.png 已去除原号牌号码、原档案编号
 * 以及检验有效期至后面的原日期值，前端负责写入新值。
 * 公共能力（字体/加载/绘制/下载/随机数据）复用 @/utils 下工具。
 */

import { loadImage, fillText } from '@/utils/canvasImage'
import { randomPlateNo, randomArchiveNo } from '@/utils/randomData'

const SRC = '/templates/vehicle-license-back-clean.png?v=3'
const W = 1080
const H = 769

// 号牌号码实测：青JZ373R → x254~439, y84~125，中心 y≈104.5
// size=36（比底图原字号小 8）：字高≈34，右缘 x≈414，观感更协调
// centerY=108.5：相比原位置下移 4px
const PLATE = { x: 254, centerY: 108.5, size: 36 }

// 档案编号实测：12 位数字 x644~902, y91~117，中心 y≈104
// 原图总宽 258px；一次连续绘制 + size=38 总宽≈252px，字符紧凑自然（非逐字排布）
const ARCHIVE = { x: 644, centerY: 104, size: 38 }

// 检验有效期至日期实测：2048年06月 → 值从 x523 起（"2"左缘）到 x774（"月"右缘），中心 y≈541.5
// 标签"检验有效期至"位于 x266~523，右侧保留"豫A"印章；size=38 与底图字高一致
const INSPECTION_DATE = { x: 523, centerY: 541.5, size: 38 }

export interface VehicleLicenseBackResult {
  url: string
}

/**
 * 生成行驶证副页图片：写入车牌号、档案编号与检验有效期至日期。
 */
export async function generateVehicleLicenseBack(
  plateNo: string,
  archiveNo: string,
  inspectionDate?: string,
): Promise<VehicleLicenseBackResult> {
  const tpl = await loadImage(SRC)
  const canvas = document.createElement('canvas')
  canvas.width = W
  canvas.height = H
  const ctx = canvas.getContext('2d')!
  ctx.drawImage(tpl, 0, 0)
  // 行驶证车牌/证号字号 weight=500 匹配模板观感（非加粗）
  fillText(ctx, plateNo, PLATE, { weight: 500 })
  fillText(ctx, archiveNo, ARCHIVE, { weight: 500 })
  fillText(ctx, inspectionDate ?? formatInspectionDate(), INSPECTION_DATE, { weight: 500 })
  return { url: canvas.toDataURL('image/png') }
}

/** 返回当前日期 +15 个月的日期，格式 YYYY年MM月（如 2028年02月） */
export function formatInspectionDate(): string {
  const d = new Date()
  d.setMonth(d.getMonth() + 15)
  const year = d.getFullYear()
  const month = String(d.getMonth() + 1).padStart(2, '0')
  return `${year}年${month}月`
}
