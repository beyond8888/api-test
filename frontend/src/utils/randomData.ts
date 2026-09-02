/**
 * 随机数据生成公共能力 —— 供所有证件/图片生成器复用。
 *
 * 集中管理：车牌号、VIN、发动机号码、身份证号、姓名、住址、民族等
 * 各类随机数据的生成逻辑，避免各 composable 重复定义。
 */

import { AREA_CODES } from '@/composables/areaCodes'

/** 省份简称（车辆号牌/道路运输证共用） */
export const PROVINCES = [
  '京', '津', '沪', '渝', '冀', '豫', '云', '辽', '黑', '湘',
  '皖', '鲁', '新', '苏', '浙', '赣', '鄂', '桂', '甘', '晋',
  '蒙', '陕', '吉', '闽', '贵', '粤', '青', '藏', '川', '宁', '琼',
]

/** 车牌地市字母（排除 I、O 易混淆） */
export const LETTERS = 'ABCDEFGHJKLMNPQRSTUVWXYZ'
/** 车牌后段字母/数字（排除 I、O） */
export const ALPHANUM = 'ABCDEFGHJKLMNPQRSTUVWXYZ0123456789'
/** VIN / 发动机号码合法字符（排除 I、O、Q） */
export const VIN_CHARS = 'ABCDEFGHJKLMNPRSTUVWXYZ0123456789'

/** 从数组随机取一个元素 */
export function sample<T>(arr: T[]): T {
  return arr[Math.floor(Math.random() * arr.length)]
}

/** 从给定字符集随机取一个字符 */
export function randomChar(chars: string): string {
  return chars[Math.floor(Math.random() * chars.length)]
}

/** 随机生成长度为 len 的数字串 */
export function randomDigits(len: number): string {
  let s = ''
  for (let i = 0; i < len; i++) s += Math.floor(Math.random() * 10)
  return s
}

/** 随机生成一个普通 7 位车牌号，如 青JZ373R */
export function randomPlateNo(): string {
  const province = sample(PROVINCES)
  const city = randomChar(LETTERS)
  const tail = Array.from({ length: 5 }, () => randomChar(ALPHANUM)).join('')
  return `${province}${city}${tail}`
}

/** 随机生成 17 位车辆识别代号（VIN），如 LSVGH61N1Y0001234 */
export function randomVIN(): string {
  return Array.from({ length: 17 }, () => randomChar(VIN_CHARS)).join('')
}

/** 随机生成 8~12 位发动机号码，如 444176961362 */
export function randomEngineNo(): string {
  const len = 8 + Math.floor(Math.random() * 5) // 8~12
  return Array.from({ length: len }, () => randomChar(VIN_CHARS)).join('')
}

/** 随机生成 12 位档案编号，如 462156315330 */
export function randomArchiveNo(): string {
  return randomDigits(12)
}

/** 随机生成 12 位经营许可证号，如 337374899868 */
export function randomLicenseNo(): string {
  return randomDigits(12)
}

/** 身份证号第 17 位：奇数男，偶数女 */
export function genderFromId(idNumber: string): string {
  const n = Number.parseInt(idNumber[16], 10)
  return Number.isNaN(n) || n % 2 === 1 ? '男' : '女'
}

const ADDR_PREFIX = ['北京市朝阳区', '上海市浦东新区', '广州市天河区', '深圳市南山区', '杭州市西湖区', '成都市武侯区', '南京市鼓楼区', '武汉市洪山区']
const ADDR_ROAD = ['幸福路', '建设路', '中山路', '人民路', '光明街', '和平里']

/** 随机生成一个常住地址，如 北京市朝阳区幸福路88号 */
export function randomAddress(): string {
  const prefix = sample(ADDR_PREFIX)
  const road = sample(ADDR_ROAD)
  const no = 1 + Math.floor(Math.random() * 200)
  return `${prefix}${road}${no}号`
}

const NATIONS = ['汉', '汉', '汉', '汉', '汉', '汉', '汉', '汉', '汉', '壮', '回', '满', '苗', '彝', '土家', '藏', '蒙古', '维吾尔']

/** 随机生成一个民族（汉族为主） */
export function randomNation(): string {
  return sample(NATIONS)
}

const SURNAMES = ['王', '李', '张', '刘', '陈', '杨', '黄', '赵', '周', '吴', '徐', '孙', '马', '朱', '胡', '郭', '何', '高', '林', '罗', '郑', '梁', '谢', '宋', '唐', '许', '韩', '冯', '邓', '曹', '彭', '曾', '萧', '田', '董', '袁', '潘', '于', '蒋', '蔡', '余', '杜', '叶', '程', '苏', '魏', '吕', '丁', '任', '沈']
const GIVEN = ['伟', '芳', '娜', '敏', '静', '丽', '强', '磊', '军', '洋', '勇', '艳', '杰', '娟', '涛', '明', '超', '秀英', '霞', '平', '刚', '桂英', '华', '玲', '飞', '玉兰', '萍', '红', '建华', '建国', '建军', '建平', '海', '峰', '浩', '亮', '晨', '欣', '思', '宇', '婷', '雪', '琳']

/** 随机生成一个中文姓名，如 王伟 */
export function randomChineseName(): string {
  return sample(SURNAMES) + sample(GIVEN)
}

/**
 * 随机生成一个合法的 18 位身份证号：
 * 前 6 位取真实行政区划代码，第 7~14 位为出生日期，末位为校验码。
 */
export function randomIdNumber(): string {
  const area = sample(AREA_CODES)
  const year = 1960 + Math.floor(Math.random() * 35)
  const month = String(1 + Math.floor(Math.random() * 12)).padStart(2, '0')
  const day = String(1 + Math.floor(Math.random() * 28)).padStart(2, '0')
  const seq = String(100 + Math.floor(Math.random() * 899))
  const base17 = `${area}${year}${month}${day}${seq}`
  const weights = [7, 9, 10, 5, 8, 4, 2, 1, 6, 3, 7, 9, 10, 5, 8, 4, 2]
  const checkCodes = '10X98765432'
  let sum = 0
  for (let i = 0; i < 17; i++) sum += Number.parseInt(base17[i]) * weights[i]
  return base17 + checkCodes[sum % 11]
}
