/**
 * 道路运输从业资格证图片生成器 —— 仅替换姓名和证号。
 *
 * 模板 qualification-cert-clean.png 已去除姓名和证号，
 * 前端只写入与身份证一致的新数据。
 * 公共能力（字体/加载/绘制/下载）复用 @/utils 下工具。
 */

import { loadImage, fillText } from '@/utils/canvasImage'

const SRC = '/templates/qualification-cert-clean.png?v=3'
const W = 1152
const H = 1620

// 写字坐标（基于 元秀-从业资格证.png 1152×1620 标定）
const NAME = { x: 374, centerY: 509, size: 34 }
const LICENSE_NO = { x: 395, centerY: 827, size: 28 }

export interface QualificationCertResult {
  url: string
}

/**
 * 生成从业资格证图片：仅写入姓名和证号。
 */
export async function generateQualificationCert(
  name: string,
  idNumber: string,
): Promise<QualificationCertResult> {
  const tpl = await loadImage(SRC)
  const canvas = document.createElement('canvas')
  canvas.width = W
  canvas.height = H
  const ctx = canvas.getContext('2d')!
  ctx.drawImage(tpl, 0, 0)

  fillText(ctx, name, NAME)
  fillText(ctx, idNumber, LICENSE_NO, { font: 'mono' })

  return { url: canvas.toDataURL('image/png') }
}
