<template>
  <div class="schedule-page">
    <!-- Page Header -->
    <div class="page-top">
      <div class="top-actions">
        <n-select
          v-model:value="selectedAssignees"
          :options="assigneeOptions"
          multiple
          clearable
          size="small"
          placeholder="Filter by assignee"
          class="filter-select"
        />
        <button class="create-btn" @click="openCreate()">+ Create</button>
      </div>
    </div>

    <!-- Calendar Toolbar -->
    <div class="cal-toolbar">
      <div class="toolbar-nav">
        <button class="today-btn" @click="goToday">Today</button>
        <div class="nav-arrows">
          <button @click="prev">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="15 18 9 12 15 6"/></svg>
          </button>
          <button @click="next">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 18 15 12 9 6"/></svg>
          </button>
        </div>
      </div>
      <h2 class="cal-title">{{ title }}</h2>
    </div>

    <!-- Month Grid -->
    <div class="cal-month" @wheel.prevent="onWheel" @touchstart="onTouchStart" @touchmove.prevent @touchend="onTouchEnd">
      <!-- Day-of-week header -->
      <div class="cal-dow">
        <span v-for="d in DOW_LABELS" :key="d.key"
          :class="{ weekend: d.weekend }">{{ d.label }}</span>
      </div>

      <!-- Grid rows -->
      <div class="cal-grid-body" :key="title">
        <div v-for="(row, ri) in calendarRows" :key="ri" class="cal-row" :style="{ minHeight: `${rowMinHeight(row.maxVisibleLanes)}px` }">
          <!-- Cells layer -->
          <div class="cal-cells">
            <div v-for="day in row.days" :key="day.date"
              class="cal-cell"
              :data-date="day.date"
              :class="{
                'out-month': !day.inMonth,
                'is-weekend': day.isWeekend,
                'is-today': day.isToday,
                'drag-over': dragOverDate === day.date,
              }"
              @dblclick="openCreate(day.date)">
              <!-- Holiday badge -->
              <span v-if="day.holidayName" class="cal-holiday">{{ day.holidayName }}</span>
              <!-- Day number -->
              <span class="cal-date" :class="{ today: day.isToday, 'out-month': !day.inMonth }">{{ day.dayNum }}</span>
              <!-- Overflow -->
              <button v-if="day.overflow > 0" class="cal-more-btn" @click.stop="openMore(day.date)" @dblclick.stop="openCreate(day.date)">
                +{{ day.overflow }} more
              </button>
            </div>
          </div>

          <!-- Bars layer -->
          <div class="cal-bars" :class="{ dragging: !!dragState }">
            <n-tooltip v-for="bar in row.bars" :key="bar.id" trigger="hover" :delay="200">
              <template #trigger>
                <div
                  class="cal-bar"
                  :data-id="bar.id"
                  :class="{ dragging: dragState?.id === bar.id }"
                  :style="barStyle(bar)"
                  @dblclick.stop="editAssignment(bar)"
                  @mousedown="onMouseDown(bar, $event)">
                  <span class="bar-title">{{ bar.title }}</span>
                </div>
              </template>
              <span>{{ barTooltip(bar) }}</span>
            </n-tooltip>
          </div>
        </div>
      </div>
    </div>

    <!-- Create/Edit Modal -->
    <n-modal v-model:show="showModal" style="width:440px" :mask-closable="false">
      <div class="modal-form">
        <div class="form-header">
          <span class="form-header-title">{{ editingId ? 'Edit Event' : 'New Event' }}</span>
        </div>
        <input
          ref="titleInput"
          v-model="formTitle"
          placeholder="Event title"
          class="form-title-input"
          @keyup.enter="save"
        />
        <div class="form-section">
          <label class="form-label">Dates</label>
          <div class="form-date-row">
            <n-date-picker v-model:value="formStartTs" type="date" style="flex:1" size="small" :actions="[]" placeholder="Start date" />
            <span class="form-date-arrow">&rarr;</span>
            <n-date-picker v-model:value="formEndTs" type="date" style="flex:1" size="small" :actions="[]" placeholder="End date" />
          </div>
        </div>
        <div class="form-section">
          <label class="form-label">Team</label>
          <div class="form-team-row">
            <n-select v-model:value="formRole" :options="ROLE_OPTIONS" clearable placeholder="Role" style="width:130px" size="small" />
            <n-input v-model:value="formAssignee" placeholder="Assignee name" size="small" />
          </div>
        </div>
        <div class="form-footer">
          <button v-if="editingId" class="form-delete-btn" @click="deleteAssignment">Delete event</button>
          <span style="flex:1"></span>
          <button class="form-btn" @click="showModal = false">Cancel</button>
          <button class="form-btn primary" @click="save">Save</button>
        </div>
      </div>
    </n-modal>

    <!-- More events modal -->
    <n-modal v-model:show="showMoreModal" style="width:440px" :mask-closable="true">
      <div class="more-modal">
        <div class="more-header">
          <h3>{{ moreDate }}</h3>
          <button class="form-btn" @click="showMoreModal = false">Close</button>
        </div>
        <div class="more-list">
          <div v-for="ev in moreList" :key="ev.id" class="more-item" @click="editFromMore(ev)">
            <span class="more-dot" :style="{ background: eventColor(ev, projects) }"></span>
            <div class="more-info">
              <div class="more-title">{{ ev.title }}</div>
              <div class="more-meta">
                {{ ev.start_date }}
                <span v-if="ev.start_date !== ev.end_date"> &mdash; {{ ev.end_date }}</span>
                <span v-if="showProjectBadge(ev)" class="more-project-badge">{{ projectNameOf(ev, projects) }}</span>
              </div>
            </div>
            <svg class="more-arrow" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 18 15 12 9 6"/></svg>
          </div>
          <div v-if="moreList.length === 0" class="more-empty">No events on this day</div>
        </div>
      </div>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, nextTick } from 'vue'
import { NModal, NDatePicker, NSelect, NInput, NTooltip } from 'naive-ui'
import type { ScheduleAssignment, ScheduleProject } from '@/types'
import {
  fmt, parseDate, addDays, daysBetween,
  pickColor, eventColor,
  computeCalendarRows, barStyle, barTooltip, projectNameOf, rowMinHeight,
  DOW_LABELS, ROLE_OPTIONS,
} from '@/composables/useScheduleCalendar'
import {
  fetchAllProjects, createProject,
  fetchAssignments, createAssignment, updateAssignment, patchAssignment,
  deleteAssignment as removeAssignment,
  fetchHolidays, fetchAssignees,
} from '@/services/schedule'

// ── Drag state ──
interface DragState {
  id: number
  startDate: string
  endDate: string
  spanDays: number
  ghost: HTMLElement
  original: HTMLElement
  offsetX: number
  offsetY: number
}

// ── State ──
const assignments = ref<ScheduleAssignment[]>([])
const projects = ref<ScheduleProject[]>([])
const assignees = ref<string[]>([])
const holidays = ref<Record<string, string>>({})
const currentDate = ref(new Date())
const selectedAssignees = ref<string[]>([])
const showModal = ref(false)
const editingId = ref<number | null>(null)
const titleInput = ref<HTMLInputElement | null>(null)
const dragOverDate = ref<string | null>(null)
const showMoreModal = ref(false)
const moreDate = ref<string>('')

const formTitle = ref('')
const formRole = ref<string | null>(null)
const formAssignee = ref('')
const formStartTs = ref<number | null>(null)
const formEndTs = ref<number | null>(null)

// ── Computed ──
const title = computed(() => {
  const d = currentDate.value
  return `${d.getFullYear()}年${d.getMonth() + 1}月`
})
const assigneeOptions = computed(() => assignees.value.map((a) => ({ label: a, value: a })))
const goToday = () => { currentDate.value = new Date() }
const prev = () => { currentDate.value = new Date(currentDate.value.getFullYear(), currentDate.value.getMonth() - 1, 1) }
const next = () => { currentDate.value = new Date(currentDate.value.getFullYear(), currentDate.value.getMonth() + 1, 1) }

const calendarRows = computed(() =>
  computeCalendarRows(currentDate.value, assignments.value, holidays.value, projects.value)
)

const moreList = computed(() => {
  if (!moreDate.value) return []
  return assignments.value
    .filter((s) => s.start_date <= moreDate.value && s.end_date >= moreDate.value)
    .sort((a, b) => a.start_date.localeCompare(b.start_date) || a.end_date.localeCompare(b.end_date))
})

function openMore(date: string) {
  moreDate.value = date
  showMoreModal.value = true
}

// ── CRUD ──
const formStart = computed(() => formStartTs.value ? fmt(new Date(formStartTs.value)) : null)
const formEnd = computed(() => formEndTs.value ? fmt(new Date(formEndTs.value)) : null)

async function openCreate(dateStr?: string) {
  editingId.value = null
  formTitle.value = ''
  formRole.value = null
  formAssignee.value = ''
  const d = dateStr ? parseDate(dateStr) : new Date()
  const ts = d.getTime()
  formStartTs.value = ts
  formEndTs.value = ts
  showModal.value = true
  nextTick(() => titleInput.value?.focus())
}

function editAssignment(ev: ScheduleAssignment) {
  editingId.value = ev.id
  formTitle.value = ev.title
  formRole.value = ev.role || null
  formAssignee.value = ev.assignee || ''
  formStartTs.value = parseDate(ev.start_date).getTime()
  formEndTs.value = parseDate(ev.end_date).getTime()
  showModal.value = true
}

function editFromMore(ev: ScheduleAssignment) {
  showMoreModal.value = false
  editAssignment(ev)
}

// Only render the project badge when the project name carries info the title
// doesn't already show (projects are often auto-named after the title).
function showProjectBadge(ev: ScheduleAssignment): boolean {
  const name = projectNameOf(ev, projects.value)
  return !!name && name !== ev.title && !ev.title?.includes(name)
}

async function save() {
  if (!formTitle.value.trim()) formTitle.value = '(no title)'
  // Date validation: start must be <= end (swap timestamps if reversed)
  const ss = formStart.value || fmt(new Date())
  const es = formEnd.value || ss
  if (ss > es && formStartTs.value && formEndTs.value) {
    const tmp = formStartTs.value
    formStartTs.value = formEndTs.value
    formEndTs.value = tmp
  }
  const projectId = await findOrCreateProject(formTitle.value.trim())
  const data = {
    title: formTitle.value,
    start_date: ss,
    end_date: es,
    role: formRole.value || '',
    assignee: formAssignee.value.trim(),
    project: projectId,
  }
  try {
    if (editingId.value) {
      await updateAssignment(editingId.value, data)
    } else {
      await createAssignment(data)
    }
    showModal.value = false
    await loadAssignments()
  } catch {
    // error toast handled by global interceptor
  }
}

async function deleteAssignment() {
  if (!editingId.value) return
  try {
    await removeAssignment(editingId.value)
    showModal.value = false
    await loadAssignments()
  } catch {
    // error toast handled by global interceptor
  }
}

async function findOrCreateProject(name: string) {
  if (!name) return null
  const ex = projects.value.find((p) => p.name === name)
  if (ex) return ex.id
  const color = pickColor(projects.value)
  const newProject = await createProject({ name, color })
  projects.value.push(newProject)
  return newProject.id
}

// ── Drag & Drop ──
let dragState: DragState | null = null
let mouseStart: { x: number; y: number; bar: ScheduleAssignment; el: HTMLElement } | null = null

function startDrag(bar: ScheduleAssignment, el: HTMLElement) {
  const rect = el.getBoundingClientRect()
  const ghost = el.cloneNode(true) as HTMLElement
  ghost.className = 'cal-drag-ghost'
  ghost.style.width = `${rect.width}px`
  ghost.style.height = `${rect.height}px`
  ghost.style.left = `${rect.left}px`
  ghost.style.top = `${rect.top}px`
  document.body.appendChild(ghost)

  dragState = {
    id: bar.id, startDate: bar.start_date, endDate: bar.end_date,
    spanDays: daysBetween(bar.start_date, bar.end_date) + 1,
    ghost, original: el,
    offsetX: mouseStart ? mouseStart.x - rect.left : 0,
    offsetY: mouseStart ? mouseStart.y - rect.top : 0,
  }
  el.classList.add('dragging')
  document.body.style.cursor = 'grabbing'
  document.body.style.userSelect = 'none'
}

function onMouseDown(bar: ScheduleAssignment, e: MouseEvent) {
  if (e.button !== 0) return
  mouseStart = { x: e.clientX, y: e.clientY, bar, el: e.currentTarget as HTMLElement }
  document.addEventListener('mousemove', onMouseMove)
  document.addEventListener('mouseup', onMouseUp)
}

function onMouseMove(e: MouseEvent) {
  if (!mouseStart) return
  if (!dragState) {
    const dx = Math.abs(e.clientX - mouseStart.x)
    const dy = Math.abs(e.clientY - mouseStart.y)
    if (dx < 6 && dy < 6) return
    startDrag(mouseStart.bar, mouseStart.el)
    if (!dragState) return
  }
  dragState.ghost.style.left = `${e.clientX - dragState.offsetX}px`
  dragState.ghost.style.top = `${e.clientY - dragState.offsetY}px`
  const target = document.elementFromPoint(e.clientX, e.clientY)
  const cell = target?.closest('.cal-cell') as HTMLElement | null
  dragOverDate.value = cell?.getAttribute('data-date') || null
}

async function onMouseUp(e: MouseEvent) {
  if (dragState) {
    const target = document.elementFromPoint(e.clientX, e.clientY)
    const cell = target?.closest('.cal-cell') as HTMLElement | null
    const date = cell?.getAttribute('data-date')
    if (date && dragState.id) {
      const delta = daysBetween(dragState.startDate, date)
      if (delta !== 0) {
        try {
          await patchAssignment(dragState.id, {
            start_date: addDays(dragState.startDate, delta),
            end_date: addDays(dragState.endDate, delta),
          })
          await loadAssignments()
        } catch {
          // error toast handled by global interceptor
        }
      }
    }
    dragState.original.classList.remove('dragging')
    dragState.ghost.remove()
    dragState = null
    dragOverDate.value = null
    document.body.style.cursor = ''
    document.body.style.userSelect = ''
  }
  mouseStart = null
  document.removeEventListener('mousemove', onMouseMove)
  document.removeEventListener('mouseup', onMouseUp)
}

// ── Data loading ──
// Split into meta (projects/assignees, loaded once), holidays (per year) and
// assignments (per month). Flipping months only re-fetches assignments so the
// calendar stays responsive instead of reloading everything on every scroll.
async function loadMeta() {
  const [pj, as] = await Promise.all([fetchAllProjects(), fetchAssignees()])
  projects.value = pj
  assignees.value = as
}

async function loadHolidays(y: number) {
  try {
    const hl = await fetchHolidays(y)
    const hm: Record<string, string> = {}
    if (Array.isArray(hl)) for (const h of hl) hm[h.date] = h.name
    holidays.value = hm
  } catch {
    // error toast handled by global interceptor
  }
}

async function loadAssignments() {
  const y = currentDate.value.getFullYear()
  const m = currentDate.value.getMonth() + 1
  const params: Record<string, unknown> = { year: y, month: m }
  if (selectedAssignees.value.length) params.assignee = selectedAssignees.value.join(',')
  try {
    assignments.value = await fetchAssignments(params)
  } catch {
    // error toast handled by global interceptor
  }
}

let lastHolidayYear = 0

// ── Wheel / touch to change month ──
// Default scroll suppression is handled declaratively via template modifiers
// (@wheel.prevent / @touchmove.prevent) so the page never scrolls while the
// pointer/finger is over the calendar. These handlers only drive the flip.
let lastWheelTs = 0
let touchStartY = 0
let touchStartX = 0

function onWheel(e: WheelEvent) {
  // Negligible nudges (trackpad micro-jitter) are ignored for the flip, but
  // the page scroll is already suppressed by the template's .prevent.
  if (Math.abs(e.deltaY) < 8) return
  const now = Date.now()
  if (now - lastWheelTs < 350) return
  lastWheelTs = now
  if (e.deltaY > 0) next() // scroll down → next month
  else prev()              // scroll up → previous month
}

function onTouchStart(e: TouchEvent) {
  touchStartY = e.touches[0].clientY
  touchStartX = e.touches[0].clientX
}

function onTouchEnd(e: TouchEvent) {
  const t = e.changedTouches[0]
  const dy = t.clientY - touchStartY
  const dx = t.clientX - touchStartX
  // Require a mostly-vertical swipe with enough travel distance.
  if (Math.abs(dy) > 50 && Math.abs(dy) > Math.abs(dx) * 1.5) {
    if (dy < 0) next() // swipe up → next month
    else prev()        // swipe down → previous month
  }
  touchStartY = 0
  touchStartX = 0
}

onMounted(async () => {
  await loadMeta()
  const y = currentDate.value.getFullYear()
  lastHolidayYear = y
  await loadHolidays(y)
  await loadAssignments()
})

watch(currentDate, async () => {
  const y = currentDate.value.getFullYear()
  if (y !== lastHolidayYear) {
    lastHolidayYear = y
    await loadHolidays(y)
  }
  await loadAssignments()
})
watch(selectedAssignees, loadAssignments)
</script>

<style scoped>
/* ============================================================
   Page
   ============================================================ */
.schedule-page {
  max-width: 1080px;
  margin: 0 auto;
  padding: 28px 0 48px;
}

/* ============================================================
   Page Header overrides
   ============================================================ */
.page-top { margin-bottom: 16px; }
.filter-select {
  width: 200px;
}

/* Create button */
.create-btn {
  padding: 8px 20px;
  border: none;
  border-radius: 6px;
  background: var(--brand-grad);
  color: #fff;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  white-space: nowrap;
  transition: filter var(--duration-fast), box-shadow var(--duration-fast);
  box-shadow: var(--shadow-glow);
}
.create-btn:hover {
  filter: brightness(1.08);
  box-shadow: 0 0 28px rgba(99, 102, 241, 0.35);
}

/* ============================================================
   Calendar Toolbar
   ============================================================ */
.cal-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 14px;
}
.toolbar-nav {
  display: flex;
  align-items: center;
  gap: 10px;
}

/* Today button */
.today-btn {
  padding: 6px 16px;
  border: 1px solid var(--border);
  border-radius: 6px;
  background: var(--bg-subtle);
  font-size: 13px;
  color: var(--text-secondary);
  cursor: pointer;
  font-weight: 500;
  transition: background var(--duration-fast), border-color var(--duration-fast);
}
.today-btn:hover {
  background: var(--bg-hover);
  border-color: var(--text-muted);
}

/* Nav arrows */
.nav-arrows {
  display: flex;
}
.nav-arrows button {
  width: 34px;
  height: 34px;
  border: 1px solid var(--border);
  background: var(--bg-subtle);
  color: var(--text-secondary);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background var(--duration-fast), border-color var(--duration-fast);
}
.nav-arrows button:first-child {
  border-radius: 6px 0 0 6px;
}
.nav-arrows button:last-child {
  border-radius: 0 6px 6px 0;
  margin-left: -1px;
}
.nav-arrows button:hover {
  background: var(--bg-hover);
  color: var(--text);
}

/* Month title */
.cal-title {
  font-size: 22px;
  font-weight: 600;
  color: var(--text);
  margin: 0;
  letter-spacing: -0.3px;
}

/* ============================================================
   Month Grid Container
   ============================================================ */
.cal-month {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  overflow: hidden;
  box-shadow: var(--shadow-xs);
  display: flex;
  flex-direction: column;
  min-height: 0;
}

/* ============================================================
   Day of Week Header
   ============================================================ */
.cal-dow {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  padding: 8px 0;
  background: var(--bg-subtle);
  border-bottom: 1px solid var(--border);
}
.cal-dow span {
  text-align: center;
  font-size: 13px;
  font-weight: 700;
  text-transform: uppercase;
  color: var(--text-muted);
}
.cal-dow span.weekend {
  color: var(--method-get);
}

/* ============================================================
   Grid Body
   ============================================================ */
.cal-grid-body {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 0;
  animation: calFade 180ms ease-out;
}
@keyframes calFade {
  from { opacity: 0; transform: translateY(6px); }
  to   { opacity: 1; transform: translateY(0); }
}

.cal-row {
  position: relative;
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  flex: 1;
  /* Row height is set inline from rowMinHeight() based on the actual number of
     visible lanes for that week. The default 84px covers 2 visible lanes. */
  min-height: 84px;
}

/* ============================================================
   Cells
   ============================================================ */
.cal-cells {
  position: absolute;
  inset: 0;
  display: grid;
  grid-template-columns: repeat(7, 1fr);
}

.cal-cell {
  position: relative;
  padding: 4px 5px 3px;
  background: var(--bg-card);
  border-right: 1px solid var(--border);
  border-bottom: 1px solid var(--border);
  cursor: default;
  transition: background var(--duration-fast);
  display: flex;
  flex-direction: column;
  align-items: flex-end;
}
.cal-cell:nth-child(7n) {
  border-right: none;
}

/* Cell variants */
.cal-cell.is-weekend {
  background: rgba(255, 255, 255, 0.015);
}
.cal-cell.out-month {
  /* Make out-of-month days visibly recessive against the current month. */
  background: var(--nest-1);
}
.cal-cell.out-month:hover {
  background: var(--nest-2);
}
.cal-cell.is-today {
  background: var(--brand-bg);
  box-shadow: inset 0 1px 0 rgba(99, 102, 241, 0.15);
}
.cal-cell:hover {
  background: var(--bg-hover);
}
.cal-cell.drag-over {
  background: var(--brand-bg);
  box-shadow: inset 0 0 0 2px var(--brand);
}

/* Date number */
.cal-date {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  font-size: 14px;
  font-weight: 500;
  color: var(--text-secondary);
  line-height: 1;
  transition: background var(--duration-fast), color var(--duration-fast);
}
.cal-date.today,
.cal-cell.out-month .cal-date.today {
  background: var(--brand);
  color: #fff;
  font-weight: 700;
  opacity: 1;
  font-size: 14px;
  box-shadow: 0 0 6px rgba(99, 102, 241, 0.3);
}
.cal-date.out-month {
  color: var(--text-muted);
  opacity: 0.5;
  font-size: 13px;
  font-weight: 400;
}

/* Holiday badge */
.cal-holiday {
  position: absolute;
  top: 5px;
  left: 6px;
  font-size: 10px;
  font-weight: 600;
  color: var(--error);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: calc(100% - 36px);
  line-height: 1;
}

/* More events button */
.cal-more-btn {
  position: absolute;
  bottom: 5px;
  left: 8px;
  right: 8px;
  padding: 1px 0 0;
  border: none;
  background: none;
  font-size: 11px;
  font-weight: 500;
  color: var(--text-muted);
  cursor: pointer;
  text-align: left;
  transition: color var(--duration-fast);
}
.cal-more-btn:hover {
  color: var(--method-get);
}

/* ============================================================
   Bars layer
   ============================================================ */
.cal-bars {
  position: absolute;
  inset: 0;
  pointer-events: none;
}
.cal-bars.dragging .cal-bar {
  pointer-events: none;
}

.cal-bar {
  position: absolute;
  height: 18px;
  margin-top: 0;
  border-radius: 4px;
  padding: 0 6px 0 5px;
  font-size: 11px;
  font-weight: 600;
  line-height: 18px;
  color: #fff;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  cursor: grab;
  pointer-events: auto;
  user-select: none;
  box-sizing: border-box;
  /* A single thin inner highlight edge instead of a heavy shadow/border,
     so stacked bars look separate but not like one is layered under another. */
  border: 1px solid rgba(255, 255, 255, 0.35);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.15);
  transition: transform var(--duration-fast), box-shadow var(--duration-fast);
  display: flex;
  align-items: center;
  gap: 4px;
}
.cal-bar:hover {
  transform: translateY(-1px);
  box-shadow: 0 2px 5px rgba(0, 0, 0, 0.15), inset 0 1px 0 rgba(255, 255, 255, 0.15);
  z-index: 10;
  cursor: grab;
}
.cal-bar:active {
  cursor: grabbing;
}
.cal-bar.dragging {
  opacity: 0.3;
}

.bar-title {
  overflow: hidden;
  text-overflow: ellipsis;
}

/* Drag ghost */
:deep(.cal-drag-ghost) {
  position: fixed;
  z-index: 9999;
  pointer-events: none;
  border-radius: 5px;
  padding: 0 8px;
  font-size: 11px;
  font-weight: 600;
  color: #fff;
  line-height: 22px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  opacity: 0.85;
  box-shadow: 0 6px 18px rgba(0, 0, 0, 0.3), 0 0 0 1px rgba(0, 0, 0, 0.2);
}

/* Form Modal — surface styles moved to global stylesheet (main.css) */
.form-header {
  margin-bottom: 18px;
}

.form-title-input {
  width: 100%;
  padding: 8px 0 14px;
  border: none;
  border-bottom: 2px solid var(--border);
  font-size: 18px;
  font-weight: 500;
  color: var(--text);
  outline: none;
  background: transparent;
  margin-bottom: 20px;
  transition: border-color var(--duration-fast);
}
.form-title-input:focus {
  border-bottom-color: var(--brand);
}
.form-title-input::placeholder {
  color: var(--text-muted);
  font-weight: 400;
}

.form-section {
  margin-bottom: 16px;
}
.form-label {
  display: block;
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.6px;
  color: var(--text-muted);
  margin-bottom: 8px;
}

.form-date-row {
  display: flex;
  align-items: center;
  gap: 10px;
}
.form-date-arrow {
  color: var(--text-muted);
  font-size: 16px;
  flex-shrink: 0;
}

.form-team-row {
  display: flex;
  gap: 10px;
}

/* Footer */
.form-footer {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 8px;
  padding-top: 16px;
  border-top: 1px solid var(--border);
}
.form-btn {
  padding: 7px 18px;
  border: 1px solid var(--border);
  border-radius: 6px;
  background: var(--bg-subtle);
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  color: var(--text-secondary);
  transition: background var(--duration-fast), border-color var(--duration-fast);
}
.form-btn:hover {
  background: var(--bg-hover);
}
.form-btn.primary {
  background: var(--brand);
  color: #fff;
  border: none;
  box-shadow: var(--shadow-glow);
}
.form-btn.primary:hover {
  filter: brightness(1.1);
}

.form-delete-btn {
  border: none;
  background: none;
  color: var(--error);
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 4px;
  transition: background var(--duration-fast);
}
.form-delete-btn:hover {
  background: var(--error-bg);
}

/* More Modal — surface styles moved to global stylesheet (main.css) */
.more-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}
.more-header h3 {
  margin: 0;
  font-size: 17px;
  font-weight: 600;
  color: var(--text);
}

.more-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
  max-height: 360px;
  overflow-y: auto;
}

.more-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 12px;
  border-radius: 8px;
  cursor: pointer;
  transition: background var(--duration-fast);
}
.more-item:hover {
  background: var(--bg-hover);
}
.more-arrow {
  flex-shrink: 0;
  opacity: 0;
  color: var(--text-muted);
  transition: opacity var(--duration-fast);
}
.more-item:hover .more-arrow {
  opacity: 1;
}

.more-dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  flex-shrink: 0;
  box-shadow: 0 0 0 2px rgba(255, 255, 255, 0.1);
}

.more-info {
  flex: 1;
  min-width: 0;
}
.more-title {
  font-size: 14px;
  font-weight: 500;
  color: var(--text);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.more-meta {
  font-size: 12px;
  color: var(--text-muted);
  margin-top: 2px;
}
.more-project-badge {
  margin-left: 8px;
  padding: 1px 8px;
  border-radius: 4px;
  background: var(--bg-subtle);
  color: var(--text-secondary);
  font-size: 11px;
  font-weight: 500;
}

.more-empty {
  padding: 32px 16px;
  text-align: center;
  color: var(--text-muted);
  font-size: 13px;
}
</style>