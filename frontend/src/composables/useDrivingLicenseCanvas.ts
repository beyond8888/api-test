/**
 * 驾驶证图片生成器 —— 基于 Python 预处理的干净模板直接写文字。
 *
 * 模板 driving-license-front-clean.png / driving-license-back-clean.png
 * 已去除原变量值（标签/印章/照片/原水印保留），前端只负责写入与身份证一致的新数据。
 * 公共能力（字体/加载/绘制/下载/随机数据）复用 @/utils 下工具。
 */

import { loadImage, fillText } from '@/utils/canvasImage'
import { genderFromId, randomAddress } from '@/utils/randomData'
import { randomAreaCode } from './areaCodes'

const FRONT_SRC = '/templates/driving-license-front-clean.png?v=3'
const BACK_SRC = '/templates/driving-license-back-clean.png?v=3'
const FRONT_W = 1080
const FRONT_H = 759
const BACK_W = 1080
const BACK_H = 718

// 正面写字坐标（基于元秀-驾驶证正面 1080×759 标定）
// 当前只替换证号、姓名。证号右对齐，避免不同长度数字露出右侧旧字。
const FRONT = {
  LICENSE_NO: {
    x: 840, centerY: 181, size: 38, align: 'right' as CanvasTextAlign,
    // 顺时针微旋，让右端下沉，矫正底图证号右高左低的倾斜
    rotate: 0.4,
    rotateOrigin: { x: 443, y: 181 },
  },
  NAME: { x: 242, centerY: 235, size: 42, align: 'center' as CanvasTextAlign },
  GENDER: { x: 575, centerY: 247, size: 34 },
  NATIONALITY: { x: 775, centerY: 247, size: 34 },
  ADDRESS: { x: 205, centerY: 330, size: 36 },
  BIRTH: { x: 445, centerY: 435, size: 32 },
  FIRST_ISSUE: { x: 500, centerY: 497, size: 32 },
  CLASS: { x: 520, centerY: 570, size: 38 },
  VALID_PERIOD: { x: 215, centerY: 632, size: 32 },
}

// 副页写字坐标（基于元秀-驾驶证副页 1080×718 标定）
// 当前只替换证号、姓名。证号右对齐避免露出旧数字。
const BACK = {
  LICENSE_NO: { x: 860, centerY: 153, size: 38, align: 'right' as CanvasTextAlign },
  NAME: { x: 257, centerY: 213, size: 42, align: 'center' as CanvasTextAlign },
  FILE_NO: { x: 645, centerY: 213, size: 32 },
  RECORD_1: { x: 160, centerY: 325, size: 32 },
  RECORD_2: { x: 115, centerY: 415, size: 32 },
  RECORD_3: { x: 115, centerY: 547, size: 32 },
}

// ─── 数据生成与解析 ──────────────────────────────────────────────

function birthFromId(idNumber: string): string {
  if (idNumber.length < 14) return '1994-07-10'
  return `${idNumber.slice(6, 10)}-${idNumber.slice(10, 12)}-${idNumber.slice(12, 14)}`
}

const CLASSES = ['C1', 'C2', 'B1', 'B2', 'A1', 'A2', 'A3', 'D', 'E']
function randomClass(): string {
  return CLASSES[Math.floor(Math.random() * CLASSES.length)]
}

/**
 * 驾驶证档案编号（12 位数字）。
 *
 * 编码策略：前 4 位取真实行政区划代码的前 4 位（省市），后 8 位随机。
 * 说明：公安部门未公开档案编号的完整编码规范，网上流传的"前 4 位=省市"
 * 说法无官方依据，也无公开 API 可调用。因此这里使用国家统计局公开的
 * 行政区划代码（真实可靠）作为前 4 位，保证省市对应关系正确，
 * 后 8 位用随机数，避免硬编码无法验证的推测规则。
 */
function randomFileNo(): string {
  const areaPrefix = randomAreaCode().slice(0, 4)
  const tail = Array.from({ length: 8 }, () => Math.floor(Math.random() * 10)).join('')
  return `${areaPrefix}${tail}`
}

function randomFirstIssue(birth: string): string {
  const b = new Date(birth)
  b.setFullYear(b.getFullYear() + 18 + Math.floor(Math.random() * 13))
  b.setMonth(Math.floor(Math.random() * 12))
  b.setDate(1 + Math.floor(Math.random() * 28))
  return b.toISOString().slice(0, 10)
}

function addYears(dateStr: string, years: number): string {
  const d = new Date(dateStr)
  d.setFullYear(d.getFullYear() + years)
  return d.toISOString().slice(0, 10)
}

function formatCNDate(dateStr: string): string {
  const d = new Date(dateStr)
  const year = d.getFullYear()
  const month = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${year}年${month}月${day}日`
}

export interface DrivingLicenseData {
  licenseNo: string
  name: string
  gender: string
  nationality: string
  address: string
  birth: string
  firstIssue: string
  classType: string
  validPeriod: string
  fileNo: string
  record1: string
  record2: string
  record3: string
}

export function buildLicenseData(name: string, idNumber: string): DrivingLicenseData {
  const licenseNo = idNumber
  const gender = genderFromId(idNumber)
  const birth = birthFromId(idNumber)
  const firstIssue = randomFirstIssue(birth)
  const validTo = addYears(firstIssue, 6)
  const changeDeadline = addYears(firstIssue, 10)
  return {
    licenseNo,
    name,
    gender,
    nationality: '中国/CHN',
    address: randomAddress(),
    birth,
    firstIssue,
    classType: randomClass(),
    validPeriod: `${firstIssue} 至 ${validTo}`,
    fileNo: randomFileNo(),
    record1: `自${formatCNDate(firstIssue)}至有效起始日期有效。`,
    record2: `请于${formatCNDate(changeDeadline)}前办理变更准驾车型换证。`,
    record3: '请于每个记分周期结束后三十日内接受审验。',
  }
}

// ════════════════════════════════════════════════════════════════════
//  公开 API
// ════════════════════════════════════════════════════════════════════

export interface DrivingLicenseResult {
  frontUrl: string
  backUrl: string
}

/**
 * 生成驾驶证正副页图片：干净模板 + 与身份证一致的数据。
 * 模板本身已带"测试专用"水印，这里不再额外绘制水印。
 */
export async function generateDrivingLicense(name: string, idNumber: string): Promise<DrivingLicenseResult> {
  const [frontTpl, backTpl] = await Promise.all([loadImage(FRONT_SRC), loadImage(BACK_SRC)])
  const data = buildLicenseData(name, idNumber)

  // ── 正面 ──
  // 当前策略：仅替换证号和姓名，其他字段保留底图原样
  const frontCanvas = document.createElement('canvas')
  frontCanvas.width = FRONT_W
  frontCanvas.height = FRONT_H
  const fCtx = frontCanvas.getContext('2d')!
  fCtx.drawImage(frontTpl, 0, 0)
  fillText(fCtx, data.licenseNo, FRONT.LICENSE_NO, { font: 'mono' })
  fillText(fCtx, data.name, FRONT.NAME)
  // fillText(fCtx, data.gender, FRONT.GENDER)
  // fillText(fCtx, data.nationality, FRONT.NATIONALITY)
  // fillText(fCtx, data.address, FRONT.ADDRESS)
  // fillText(fCtx, data.birth, FRONT.BIRTH, { font: 'mono' })
  // fillText(fCtx, data.firstIssue, FRONT.FIRST_ISSUE, { font: 'mono' })
  // fillText(fCtx, data.classType, FRONT.CLASS)
  // fillText(fCtx, data.validPeriod, FRONT.VALID_PERIOD, { font: 'mono' })

  // ── 副页 ──
  // 当前策略：仅替换证号和姓名，其他字段保留底图原样
  const backCanvas = document.createElement('canvas')
  backCanvas.width = BACK_W
  backCanvas.height = BACK_H
  const bCtx = backCanvas.getContext('2d')!
  bCtx.drawImage(backTpl, 0, 0)
  fillText(bCtx, data.licenseNo, BACK.LICENSE_NO, { font: 'mono' })
  fillText(bCtx, data.name, BACK.NAME)
  fillText(bCtx, data.fileNo, BACK.FILE_NO, { font: 'mono' })
  // fillWrapped(bCtx, data.record1, BACK.RECORD_1, 820, 42)
  // fillWrapped(bCtx, data.record2, BACK.RECORD_2, 860, 42)
  // fillWrapped(bCtx, data.record3, BACK.RECORD_3, 860, 42)

  return {
    frontUrl: frontCanvas.toDataURL('image/png'),
    backUrl: backCanvas.toDataURL('image/png'),
  }
}
