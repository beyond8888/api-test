<template>
  <div class="projects-page">
    <!-- Header -->
    <div class="page-top">
      <div class="top-actions">
        <n-input
          v-model:value="searchQuery"
          placeholder="Search projects..."
          size="small"
          clearable
          class="search-input"
          @keyup.enter="handleSearch"
          @clear="handleSearch"
        >
          <template #prefix>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="opacity:0.35"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
          </template>
        </n-input>
        <n-button size="small" type="primary" @click="openCreate">
          <template #icon><span class="btn-plus">+</span></template>
          New Project
        </n-button>
      </div>
    </div>

    <!-- Loading / Empty -->
    <n-spin :show="loading" size="small" description="Loading...">
      <div v-if="!loading && projects.length === 0" class="empty-page">
        <div class="empty-graphic">
          <div class="empty-icon-circle">
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="3" width="20" height="14" rx="2" ry="2"/><line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/></svg>
          </div>
        </div>
        <div class="empty-text">{{ searchQuery ? 'No matching projects' : 'No projects yet' }}</div>
        <div class="empty-sub">
          {{ searchQuery ? 'Try a different search term' : 'Create a project and schedule team members on the calendar' }}
        </div>
        <n-button v-if="!searchQuery" type="primary" @click="openCreate" style="margin-top:20px">
          <template #icon><span class="btn-plus">+</span></template>
          Create your first project
        </n-button>
      </div>

      <!-- List -->
      <div v-else class="list-container">
        <div class="list-header">
          <span class="h-name">Project</span>
          <span class="h-assignments">Assignments</span>
          <span class="h-created">Created</span>
          <span class="h-actions">Actions</span>
        </div>

        <div
          v-for="project in projects"
          :key="project.id"
          class="list-row"
          @click="openEdit(project)"
        >
          <!-- Name -->
          <div class="row-name">
            <div class="row-name-body">
              <span class="row-name-text">{{ project.name }}</span>
              <n-tooltip v-if="project.description" trigger="hover" placement="bottom-start">
                <template #trigger>
                  <span class="row-desc-tag">desc</span>
                </template>
                {{ project.description }}
              </n-tooltip>
            </div>
          </div>

          <!-- Assignments count -->
          <div class="row-assignments">
            <span v-if="project.assignments?.length" class="assign-badge">
              <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 00-3-3.87"/><path d="M16 3.13a4 4 0 010 7.75"/></svg>
              {{ project.assignments.length }}
            </span>
            <span v-else class="assign-none">—</span>
          </div>

          <!-- Created -->
          <div class="row-created">
            <svg class="meta-icon" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>
            {{ formatDate(project.created_at) }}

          </div>

          <!-- Actions -->
          <div class="row-actions" @click.stop>
            <n-button class="act-btn edit-btn" size="small" quaternary circle title="Edit" @click="openEdit(project)">
              <template #icon>
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
              </template>
            </n-button>
            <n-popconfirm @positive-click="deleteProject(project.id)">
              <template #trigger>
                <n-button class="act-btn del-btn" size="small" quaternary circle type="error" title="Delete">
                  <template #icon>
                    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2"/></svg>
                  </template>
                </n-button>
              </template>
              Delete this project?
            </n-popconfirm>
          </div>
        </div>
      </div>
    </n-spin>

    <!-- Pagination -->
    <div v-if="totalPages > 1" class="pagination-bar">
      <span class="pagination-info">{{ paginationInfo }}</span>
      <n-pagination
        v-model:page="currentPage"
        :page-count="totalPages"
        :page-size="pageSize"
        size="small"
        show-size-picker
        :page-sizes="[10, 20, 50]"
        @update:page="handlePageChange"
        @update:page-size="handlePageSizeChange"
      />
    </div>

    <!-- Create/Edit Modal -->
    <n-modal v-model:show="showModal" style="width:600px" :mask-closable="false">
      <div class="modal-form">
        <div class="form-header">
          <span class="form-header-title">{{ editingId ? 'Edit Project' : 'New Project' }}</span>
        </div>

        <div class="form-section">
          <label class="form-label">Project name</label>
          <input
            v-model="formName"
            placeholder="e.g. User login refactor"
            class="form-title-input"
            autofocus
          />
        </div>

        <div class="form-section">
          <label class="form-label">Description</label>
          <textarea
            v-model="formDescription"
            placeholder="What this project is about"
            class="form-textarea"
            rows="3"
          ></textarea>
        </div>

        <div class="form-section">
          <label class="form-label">
            Assignments
            <span class="form-label-hint">who works on this and when</span>
          </label>
          <div class="assignment-table">
            <div class="assignment-header-row">
              <span class="a-col-role">Role</span>
              <span class="a-col-assignee">Assignee</span>
              <span class="a-col-date">Start</span>
              <span class="a-col-date">End</span>
              <span class="a-col-actions"></span>
            </div>
            <div v-for="(a, idx) in formAssignments" :key="idx" class="assignment-row">
              <n-select v-model:value="a.role" :options="ROLE_OPTIONS" clearable placeholder="Role" class="a-col-role" size="small" />
              <n-input v-model:value="a.assignee" placeholder="Name" class="a-col-assignee" size="small" />
              <n-date-picker v-model:formatted-value="a.start_date" value-format="yyyy-MM-dd" type="date" class="a-col-date" size="small" />
              <n-date-picker v-model:formatted-value="a.end_date" value-format="yyyy-MM-dd" type="date" class="a-col-date" size="small" />
              <n-button quaternary circle size="tiny" type="error" class="a-col-actions" @click="removeAssignment(idx)">
                <template #icon><span>&times;</span></template>
              </n-button>
            </div>
            <n-button dashed size="small" @click="addAssignment" style="margin-top:10px">
              + Add assignment
            </n-button>
          </div>
        </div>

        <div class="form-footer">
          <button class="form-btn" @click="showModal = false">Cancel</button>
          <button class="form-btn primary" @click="save" :disabled="!formName.trim()">Save</button>
        </div>
      </div>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import {
  NButton, NModal, NInput, NSelect, NDatePicker,
  NPopconfirm, NPagination, NSpin, NTooltip,
} from 'naive-ui'
import type { ProjectDetail, ProjectAssignment } from '@/types'
import { ROLE_OPTIONS } from '@/composables/useScheduleCalendar'
import { fetchProjects, createProject, updateProject, deleteProject as removeProject } from '@/services/schedule'
import { DEFAULT_PAGE_SIZE } from '@/utils/constants'
import { formatDate } from '@/utils/format'

const projects = ref<ProjectDetail[]>([])
const loading = ref(false)
const totalCount = ref<number | null>(null)
const currentPage = ref(1)
const pageSize = ref(DEFAULT_PAGE_SIZE)
const totalPages = ref(1)
const searchQuery = ref('')
const activeSearch = ref('')

const showModal = ref(false)
const editingId = ref<number | null>(null)
const formName = ref('')
const formDescription = ref('')
const formAssignments = ref<ProjectAssignment[]>([])

const paginationInfo = computed(() => {
  if (totalCount.value === null) return ''
  const start = (currentPage.value - 1) * pageSize.value + 1
  const end = Math.min(currentPage.value * pageSize.value, totalCount.value)
  return `${start}–${end} of ${totalCount.value} projects`
})

function resetForm() {
  editingId.value = null
  formName.value = ''
  formDescription.value = ''
  formAssignments.value = []
}

function openCreate() {
  resetForm()
  showModal.value = true
}

function openEdit(project: ProjectDetail) {
  editingId.value = project.id
  formName.value = project.name
  formDescription.value = project.description || ''
  formAssignments.value = project.assignments?.length
    ? project.assignments.map((a: ProjectAssignment) => ({ ...a }))
    : []
  showModal.value = true
}

function addAssignment() {
  const today = new Date().toISOString().slice(0, 10)
  formAssignments.value.push({
    role: '',
    assignee: '',
    start_date: today,
    end_date: today,
  })
}

function removeAssignment(idx: number) {
  formAssignments.value.splice(idx, 1)
}

async function save() {
  const payload: Record<string, unknown> = {
    name: formName.value.trim(),
    description: formDescription.value.trim(),
    assignments: formAssignments.value
      .filter((a) => a.start_date && a.end_date)
      .map((a) => ({
        role: a.role,
        assignee: a.assignee,
        start_date: a.start_date,
        end_date: a.end_date,
      })),
  }
  try {
    if (editingId.value) {
      await updateProject(editingId.value, payload)
    } else {
      await createProject(payload)
    }
    showModal.value = false
    await loadData()
  } catch {
    // error toast handled by global interceptor — keep modal open for retry
  }
}

async function deleteProject(id: number) {
  try {
    await removeProject(id)
    await loadData()
  } catch {
    await loadData()
  }
}

function handleSearch() {
  activeSearch.value = searchQuery.value.trim()
  currentPage.value = 1
  loadData()
}

function handlePageChange(page: number) {
  currentPage.value = page
  loadData()
}

function handlePageSizeChange(size: number) {
  pageSize.value = size
  currentPage.value = 1
  loadData()
}

async function loadData() {
  loading.value = true
  try {
    const params: Record<string, string | number> = {
      page: currentPage.value,
      page_size: pageSize.value,
    }
    if (activeSearch.value) {
      params.search = activeSearch.value
    }
    const data = await fetchProjects(params)
    projects.value = data.results
    totalCount.value = data.count
    totalPages.value = Math.ceil(data.count / pageSize.value)
  } catch {
    // error toast handled by global interceptor
  } finally {
    loading.value = false
  }
}

onMounted(loadData)
watch(showModal, (v) => {
  if (!v) resetForm()
})
</script>

<style scoped>
/* ---- Page wrapper ---- */
.projects-page { max-width: var(--page-max); margin: 0 auto; padding: 28px 0 48px; }
.search-input { width: 240px; }

/* ---- column widths ---- */
.h-name        { flex: 1; min-width: 0; }
.h-assignments { width: 100px; flex-shrink: 0; text-align: center; }
.h-created     { width: 140px; flex-shrink: 0; }
.h-actions     { width: 88px; flex-shrink: 0; text-align: right; padding-right: 4px; }

/* ---- row specifics ---- */
.list-row { padding: 0 16px 0 20px; cursor: pointer; }

.row-assignments {
  width: 100px; flex-shrink: 0;
  display: flex; justify-content: center;
}
.assign-badge {
  display: inline-flex; align-items: center; gap: 4px;
  font-size: 12px; font-weight: 500;
  color: var(--text-secondary);
  font-variant-numeric: tabular-nums;
}
.assign-none {
  color: var(--text-muted); opacity: 0.4;
  font-size: 14px;
}
.row-created { width: 140px; flex-shrink: 0; }
.row-actions { width: 88px; flex-shrink: 0; }

/* Name column extras */
.row-name-body {
  display: flex; align-items: center; gap: 8px;
  min-width: 0;
}
.row-desc-tag {
  font-size: 10px; font-weight: 600;
  color: var(--text-muted);
  background: var(--bg-subtle);
  padding: 1px 6px;
  border-radius: 4px;
  cursor: help; flex-shrink: 0;
  text-transform: uppercase; letter-spacing: 0.4px;
}
/* ---- Pagination ---- */
.pagination-bar {
  display: flex; align-items: center;
  justify-content: space-between;
  margin-top: 16px; padding: 0 4px;
}
.pagination-info {
  font-size: 12px; color: var(--text-muted);
}

/* ---- Form ---- */
.form-title-input {
  width: 100%;
  padding: 10px 14px;
  border: 1px solid var(--border);
  border-radius: 6px;
  font-size: 14px; color: var(--text);
  background: var(--bg-subtle);
  outline: none;
  transition: border-color var(--duration-fast);
  box-sizing: border-box;
}
.form-title-input:focus { border-color: var(--brand); }
.form-title-input::placeholder { color: var(--text-muted); }
.form-textarea {
  width: 100%;
  padding: 10px 14px;
  border: 1px solid var(--border);
  border-radius: 6px;
  font-size: 13px; color: var(--text);
  background: var(--bg-subtle);
  outline: none; resize: vertical;
  font-family: inherit;
  transition: border-color var(--duration-fast);
  box-sizing: border-box;
}
.form-textarea:focus { border-color: var(--brand); }
.form-textarea::placeholder { color: var(--text-muted); }

/* Assignment table */
.assignment-table {
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  padding: 12px 12px 8px;
  background: var(--bg-subtle);
}
.assignment-header-row {
  display: flex; align-items: center; gap: 8px;
  font-size: 10px; color: var(--text-muted);
  text-transform: uppercase; letter-spacing: 0.5px;
  font-weight: 600; margin-bottom: 8px;
}
.assignment-row {
  display: flex; align-items: center; gap: 8px;
  margin-bottom: 8px;
}
.assignment-row:last-child { margin-bottom: 0; }
.a-col-role { width: 110px; flex-shrink: 0; }
.a-col-assignee { flex: 1; min-width: 0; }
.a-col-date { width: 130px; flex-shrink: 0; }
.a-col-actions { width: 28px; flex-shrink: 0; display: flex; justify-content: center; }
</style>