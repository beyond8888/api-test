import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import {
  fetchEnvironments, createEnvironment, updateEnvironment,
  deleteEnvironment, activateEnvironment,
  type EnvironmentData,
} from '@/services/data'
import { logger } from '@/utils/logger'
import { uuid, kvToObject } from '@/utils/format'

export const useEnvironmentStore = defineStore('environment', () => {
  const environments = ref<EnvironmentData[]>([])
  const activeEnvId = ref<number | null>(null)

  const activeEnvironment = computed(() =>
    environments.value.find((e) => e.is_active) || null,
  )
  const activeVariables = computed(() => {
    const env = activeEnvironment.value
    if (!env) return {} as Record<string, string>
    return kvToObject(env.variables)
  })

  async function init() {
    try {
      environments.value = await fetchEnvironments()
      const active = environments.value.find((e) => e.is_active)
      activeEnvId.value = active?.id || null
    } catch (e) {
      logger.error('[environment] Failed to load:', e)
    }
  }

  async function createEnv(name: string): Promise<EnvironmentData | null> {
    try {
      const env = await createEnvironment(name)
      environments.value.push(env)
      return env
    } catch (e) {
      logger.error('[environment] Failed to create:', e)
      return null
    }
  }

  async function deleteEnv(id: number) {
    try {
      await deleteEnvironment(id)
      environments.value = environments.value.filter((e) => e.id !== id)
      if (activeEnvId.value === id) activeEnvId.value = null
    } catch (e) {
      logger.error('[environment] Failed to delete:', e)
    }
  }

  async function setActive(id: number) {
    try {
      await activateEnvironment(id)
      environments.value.forEach((e) => { e.is_active = e.id === id })
      activeEnvId.value = id
    } catch (e) {
      logger.error('[environment] Failed to set active:', e)
    }
  }

  async function updateVariables(id: number, variables: EnvironmentData['variables']) {
    try {
      await updateEnvironment(id, { variables })
      const env = environments.value.find((e) => e.id === id)
      if (env) env.variables = variables
    } catch (e) {
      logger.error('[environment] Failed to update variables:', e)
    }
  }

  function setVariableValue(key: string, value: string) {
    const env = activeEnvironment.value
    if (!env) return
    const existing = env.variables.find((v) => v.key === key)
    if (existing) {
      existing.value = value
      updateVariables(env.id, env.variables)
    } else {
      env.variables.push({ id: uuid(), key, value, enabled: true })
      updateVariables(env.id, env.variables)
    }
  }

  return {
    environments,
    activeId: activeEnvId,
    activeEnvironment,
    activeVariables,
    createEnv,
    deleteEnv,
    setActive,
    updateVariables,
    setVariableValue,
    init,
  }
})
