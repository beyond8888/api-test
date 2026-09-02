/**
 * Schedule API service — centralized HTTP layer for schedule endpoints.
 *
 * Every schedule/project API call goes through this module so views
 * never need to touch axios directly. The shared apiClient (via useApiClient)
 * has a response interceptor that auto-unwraps the { code, data, message }
 * envelope, so callers always receive the actual payload directly.
 */
import { useApiClient } from '@/composables/useApiClient'
import {
  API_SCHEDULE_PROJECTS,
  API_SCHEDULE_ASSIGNMENTS,
  API_SCHEDULE_HOLIDAYS,
  API_SCHEDULE_ASSIGNEES,
} from '@/utils/constants'
import type {
  ScheduleProject,
  ScheduleAssignment,
  ProjectDetail,
  PaginatedResponse,
} from '@/types'
import { extractList, fetchAllPages } from './pagination'

const { client } = useApiClient()

// ── Projects ──

export interface ProjectListParams {
  page?: number
  page_size?: number
  search?: string
  ordering?: string
}

export async function fetchProjects(
  params: ProjectListParams = {},
): Promise<PaginatedResponse<ProjectDetail>> {
  const res = await client.get(API_SCHEDULE_PROJECTS, { params })
  return res.data
}

export async function fetchAllProjects(): Promise<ScheduleProject[]> {
  return fetchAllPages<ScheduleProject>(client, API_SCHEDULE_PROJECTS)
}

export async function createProject(
  payload: Record<string, unknown>,
): Promise<ScheduleProject> {
  const res = await client.post(API_SCHEDULE_PROJECTS, payload)
  return res.data
}

export async function updateProject(
  id: number,
  payload: Record<string, unknown>,
): Promise<ProjectDetail> {
  const res = await client.put(`${API_SCHEDULE_PROJECTS}${id}/`, payload)
  return res.data
}

export async function deleteProject(id: number): Promise<void> {
  await client.delete(`${API_SCHEDULE_PROJECTS}${id}/`)
}

// ── Assignments ──

export interface AssignmentListParams {
  year?: number
  month?: number
  assignee?: string[]
  [key: string]: unknown
}

export async function fetchAssignments(
  params: AssignmentListParams = {},
): Promise<ScheduleAssignment[]> {
  return fetchAllPages<ScheduleAssignment>(client, API_SCHEDULE_ASSIGNMENTS, params)
}

export async function createAssignment(
  payload: Partial<ScheduleAssignment>,
): Promise<ScheduleAssignment> {
  const res = await client.post(API_SCHEDULE_ASSIGNMENTS, payload)
  return res.data
}

export async function updateAssignment(
  id: number,
  payload: Partial<ScheduleAssignment>,
): Promise<ScheduleAssignment> {
  const res = await client.put(`${API_SCHEDULE_ASSIGNMENTS}${id}/`, payload)
  return res.data
}

export async function patchAssignment(
  id: number,
  payload: Partial<ScheduleAssignment>,
): Promise<ScheduleAssignment> {
  const res = await client.patch(`${API_SCHEDULE_ASSIGNMENTS}${id}/`, payload)
  return res.data
}

export async function deleteAssignment(id: number): Promise<void> {
  await client.delete(`${API_SCHEDULE_ASSIGNMENTS}${id}/`)
}

// ── Holidays ──

export interface HolidayItem {
  date: string
  name: string
}

export async function fetchHolidays(year: number): Promise<HolidayItem[]> {
  try {
    const res = await client.get(API_SCHEDULE_HOLIDAYS, { params: { year } })
    return extractList(res.data) as HolidayItem[]
  } catch {
    return []
  }
}

// ── Assignees ──

export async function fetchAssignees(): Promise<string[]> {
  const res = await client.get(API_SCHEDULE_ASSIGNEES)
  return res.data as string[]
}
