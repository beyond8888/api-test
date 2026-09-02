/**
 * Core calendar utilities for ScheduleView.
 * Pure functions for date math, color assignment, grid/lane computation.
 * Keeps the view component focused on state and template.
 */

import type { ScheduleAssignment, ScheduleProject } from '@/types'
import { MS_PER_DAY, DAYS_PER_WEEK, CALENDAR_GRID_CELLS } from '@/utils/constants'
import { formatDate } from '@/utils/format'

// ── Color palette ──
// A curated set of 16 high-saturation hues spread evenly around the color
// wheel. Fewer colors = larger perceived differences between adjacent projects.
export const CALENDAR_COLORS = [
  '#ef4444', // red
  '#f97316', // orange
  '#f59e0b', // amber
  '#eab308', // yellow
  '#84cc16', // lime
  '#22c55e', // green
  '#10b981', // emerald
  '#14b8a6', // teal
  '#06b6d4', // cyan
  '#0ea5e9', // sky
  '#3b82f6', // blue
  '#6366f1', // indigo
  '#8b5cf6', // violet
  '#a855f7', // purple
  '#d946ef', // fuchsia
  '#f43f5e', // rose
]

// Visible lane budget: each row grows up to ABSOLUTE_MAX_VISIBLE_LANES when
// needed, but never below DEFAULT_VISIBLE_LANES. This keeps sparse weeks
// compact while ensuring events are only folded when there truly isn't room.
export const DEFAULT_VISIBLE_LANES = 2
export const ABSOLUTE_MAX_VISIBLE_LANES = 4

// ── Date utilities ──
// Accepts a Date (calendar-local) and delegates formatting to the shared helper.
export function fmt(d: Date): string {
  return formatDate(d.toISOString())
}

export function parseDate(s: string): Date {
  return new Date(`${s}T00:00:00`)
}

export function addDays(s: string, days: number): string {
  const d = parseDate(s)
  d.setDate(d.getDate() + days)
  return fmt(d)
}

export function daysBetween(a: string, b: string): number {
  return Math.round((parseDate(b).getTime() - parseDate(a).getTime()) / MS_PER_DAY)
}

export function isWeekend(d: string): boolean {
  const w = new Date(`${d}T00:00:00`).getDay()
  return w === 0 || w === 6
}

// ── Color utilities ──
export function pickColor(projects: ScheduleProject[]): string {
  const usage: Record<string, number> = {}
  for (const c of CALENDAR_COLORS) usage[c] = 0
  for (const p of projects) usage[p.color] = (usage[p.color] || 0) + 1
  return CALENDAR_COLORS.reduce((a, b) => (usage[a] || 0) <= (usage[b] || 0) ? a : b)
}

export function colorForName(name: string): string {
  let hash = 0
  for (let i = 0; i < name.length; i++) {
    hash = (hash << 5) - hash + name.charCodeAt(i)
    hash |= 0
  }
  return CALENDAR_COLORS[Math.abs(hash) % CALENDAR_COLORS.length]
}

export function eventColor(ev: ScheduleAssignment, projects: ScheduleProject[]): string {
  const p = projects.find((x) => x.id === ev.project)
  if (p?.color) return p.color
  return colorForName(ev.title || '')
}

export function projectNameOf(ev: ScheduleAssignment, projects: ScheduleProject[]): string {
  if (!ev.project) return ''
  return projects.find((x) => x.id === ev.project)?.name || ''
}

/**
 * Compute contrast text color using W3C relative luminance (sRGB).
 *  The 0.65 threshold is the empirical midpoint where white-on-X
 *  and black-on-X have roughly equal readability on a typical screen.
 */
export function textColor(bg: string): string {
  const r = Number.parseInt(bg.slice(1, 3), 16)
  const g = Number.parseInt(bg.slice(3, 5), 16)
  const b = Number.parseInt(bg.slice(5, 7), 16)
  const y = (0.299 * r + 0.587 * g + 0.114 * b) / 255
  return y > 0.65 ? '#1f2937' : '#ffffff'
}

// ── Day-of-week ──
export const DOW_LABELS = [
  { key: 'mon', label: '周一', weekend: false },
  { key: 'tue', label: '周二', weekend: false },
  { key: 'wed', label: '周三', weekend: false },
  { key: 'thu', label: '周四', weekend: false },
  { key: 'fri', label: '周五', weekend: false },
  { key: 'sat', label: '周六', weekend: true },
  { key: 'sun', label: '周日', weekend: true },
]

export const ROLE_OPTIONS = [
  { label: 'RD', value: 'RD' },
  { label: 'FE', value: 'FE' },
  { label: 'QA', value: 'QA' },
  { label: 'UI', value: 'UI' },
  { label: 'PM', value: 'PM' },
  { label: 'DevOps', value: 'DevOps' },
]

// ── Calendar grid computation ──
export interface CalendarDay {
  dayNum: number
  date: string
  inMonth: boolean
  isToday: boolean
  isWeekend: boolean
  holidayName: string
  overflow: number
}

export interface CalendarBar extends ScheduleAssignment {
  color: string
  textColor: string
  startCol: number
  endCol: number
  lane: number
}

export interface CalendarRow {
  days: CalendarDay[]
  bars: CalendarBar[]
  maxVisibleLanes: number
}

export function computeCalendarRows(
  currentDate: Date,
  assignments: ScheduleAssignment[],
  holidays: Record<string, string>,
  projects: ScheduleProject[],
): CalendarRow[] {
  const y = currentDate.getFullYear()
  const m = currentDate.getMonth()
  const firstDay = new Date(y, m, 1)
  // Google Calendar-style continuous month view: start on the Monday of the
  // week that contains the 1st of the month and always render 6 full weeks.
  const off = (firstDay.getDay() + 6) % 7
  const gridStart = new Date(y, m, 1 - off)
  const today = fmt(new Date())
  const days: CalendarDay[] = []

  for (let i = 0; i < CALENDAR_GRID_CELLS; i++) {
    const d = new Date(gridStart)
    d.setDate(gridStart.getDate() + i)
    const date = fmt(d)
    days.push({
      dayNum: d.getDate(),
      date,
      inMonth: d.getMonth() === m,
      isToday: date === today,
      isWeekend: isWeekend(date),
      holidayName: holidays[date] || '',
      overflow: 0,
    })
  }

  const rows: CalendarRow[] = []
  for (let i = 0; i < days.length; i += DAYS_PER_WEEK) {
    const rowDays = days.slice(i, i + DAYS_PER_WEEK)
    const rowStart = rowDays[0].date
    const rowEnd = rowDays[DAYS_PER_WEEK - 1].date

    const bars: CalendarBar[] = []
    for (const ev of assignments) {
      // Natural spanning across month boundaries: only clip to the current week.
      const displayStart = ev.start_date < rowStart ? rowStart : ev.start_date
      const displayEnd = ev.end_date > rowEnd ? rowEnd : ev.end_date

      if (!displayStart || !displayEnd || displayEnd < rowStart || displayStart > rowEnd) continue
      const color = eventColor(ev, projects)
      const sc = rowDays.findIndex((d) => d.date === displayStart)
      const ec = rowDays.findIndex((d) => d.date === displayEnd)
      bars.push({
        ...ev,
        color,
        textColor: textColor(color),
        startCol: Math.max(0, sc),
        endCol: Math.min(DAYS_PER_WEEK - 1, ec),
        lane: 0,
      })
    }

    // Stack overlapping bars into lanes. Anchor LONGER bars in the low lanes
    // first: they usually represent whole-week commitments, so they must stay
    // visible — otherwise the middle days they cover would show only "+N more"
    // and look like nothing is scheduled. Shorter bars then fill the gaps.
    const sortedBars = bars.sort((a, b) => {
      const durA = a.endCol - a.startCol
      const durB = b.endCol - b.startCol
      return durB - durA || a.startCol - b.startCol || a.endCol - b.endCol
    })
    const lanes: CalendarBar[][] = []
    for (const bar of sortedBars) {
      let placed = false
      for (const lane of lanes) {
        const overlaps = lane.some((b) => !(bar.endCol < b.startCol || bar.startCol > b.endCol))
        if (!overlaps) { lane.push(bar); placed = true; break }
      }
      if (!placed) lanes.push([bar])
    }
    const stackedBars = lanes.flatMap((lane, laneIdx) => lane.map((bar) => ({ ...bar, lane: laneIdx })))

    // Adaptive visible lanes: if the whole week only needs 2 lanes, show 2;
    // if it genuinely needs more, grow up to ABSOLUTE_MAX_VISIBLE_LANES.
    const maxVisibleLanes = Math.min(
      ABSOLUTE_MAX_VISIBLE_LANES,
      Math.max(DEFAULT_VISIBLE_LANES, lanes.length),
    )

    // Compute overflow per cell
    for (const day of rowDays) {
      const cellBars = stackedBars.filter((b) => b.start_date <= day.date && b.end_date >= day.date)
      const total = cellBars.length
      const visible = cellBars.filter((b) => b.lane < maxVisibleLanes).length
      day.overflow = Math.max(0, total - visible)
    }

    rows.push({ days: rowDays, bars: stackedBars.filter((b) => b.lane < maxVisibleLanes), maxVisibleLanes })
  }
  return rows
}

export function rowMinHeight(maxVisibleLanes: number): number {
  // Top offset starts at 22px, each lane adds 20px, bars are 18px tall,
  // and the bottom "+N more" button needs ~24px of breathing room.
  return 22 + (maxVisibleLanes - 1) * 20 + 18 + 24
}

export function barStyle(bar: CalendarBar): Record<string, string> {
  const colW = 100 / DAYS_PER_WEEK
  const left = bar.startCol * colW
  const width = (bar.endCol - bar.startCol + 1) * colW
  // Tight lane packing: 18px-tall bars with a 2px gap. The containing row
  // height is now dynamic, so this works for any visible lane count.
  const top = 22 + bar.lane * 20
  // Use equal left/right inset so the bar is centered inside its day cells
  // and its edges align cleanly with the cell borders.
  return {
    left: `calc(${left}% + 3px)`,
    width: `calc(${width}% - 6px)`,
    top: `${top}px`,
    background: bar.color,
    color: bar.textColor,
  }
}

export function barTooltip(bar: ScheduleAssignment): string {
  const lines: string[] = []
  lines.push(bar.title || '')

  const meta: string[] = []
  if (bar.assignee) meta.push(`负责人：${bar.assignee}`)
  if (bar.role) meta.push(`角色：${bar.role}`)
  if (meta.length) lines.push(meta.join(' · '))

  return lines.join('\n')
}
