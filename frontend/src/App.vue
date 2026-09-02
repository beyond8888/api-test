<template>
  <n-config-provider :theme="darkTheme" :theme-overrides="theme">
    <n-message-provider>
      <router-view v-if="isLoginPage" />
      <n-layout v-else class="app-layout">
        <AppHeader />
        <n-layout-content class="app-content">
          <router-view />
        </n-layout-content>
      </n-layout>
    </n-message-provider>
  </n-config-provider>
</template>

<script setup lang="ts">
import { computed, watch, ref } from 'vue'
import { useRoute } from 'vue-router'
import { NConfigProvider, NMessageProvider, NLayout, NLayoutContent, darkTheme } from 'naive-ui'
import { theme } from '@/styles/theme'
import AppHeader from './components/layout/AppHeader.vue'
import { useAuthStore } from '@/stores/auth'
import { useCollectionsStore } from '@/stores/collections'
import { useEnvironmentStore } from '@/stores/environment'
import { useHistoryStore } from '@/stores/history'

const route = useRoute()
const authStore = useAuthStore()

const isLoginPage = computed(() => route.meta.public === true)

// Lazy-init stores after authentication
const storesLoaded = ref(false)
async function loadStores() {
  if (storesLoaded.value || !authStore.isAuthenticated) return
  storesLoaded.value = true
  const collectionsStore = useCollectionsStore()
  const envStore = useEnvironmentStore()
  const historyStore = useHistoryStore()
  await Promise.all([
    collectionsStore.init(),
    envStore.init(),
    historyStore.init(),
  ])
}

// Watch auth state — load stores when authenticated, reset when logged out
watch(() => authStore.isAuthenticated, (authed) => {
  if (authed) loadStores()
  else storesLoaded.value = false
}, { immediate: true })


</script>

<style>
.app-layout { height: 100vh; background: transparent !important; }
.app-content { overflow: auto; background: transparent !important; }
</style>
