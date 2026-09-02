<template>
  <header class="header">
    <router-link to="/" class="logo">
      <span class="logo-mark">&#x26A1;</span>
      <span class="logo-word">ApiTester</span>
    </router-link>
    <nav class="nav">
      <router-link
        v-for="item in nav" :key="item.key" :to="item.path"
        class="nav-link" :class="{ active: isActive(item.key) }"
      >
{{ item.label }}
</router-link>
    </nav>
    <div class="header-right">
      <span class="user-name">{{ authStore.user?.username || 'User' }}</span>
      <button class="logout-btn" @click="handleLogout">退出</button>
    </div>
  </header>
</template>

<script setup lang="ts">
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

function handleLogout() {
  authStore.logout()
  router.push('/login')
}
const nav = [
  { key: 'builder', label: 'Workspace', path: '/' },
  { key: 'calendar', label: 'Calendar', path: '/calendar' },
  { key: 'projects', label: 'Projects', path: '/projects' },
  { key: 'mock', label: 'Mock', path: '/mock' },
  { key: 'tools', label: 'Tools', path: '/tools' },
  { key: 'settings', label: 'Settings', path: '/settings' },
]
function isActive(k: string) {
  if (k === 'builder') return route.path === '/'
  return route.path.startsWith(`/${k}`)
}
</script>

<style scoped>
.header {
  display: flex; align-items: center;
  height: 52px; padding: 0 24px;
  background: rgba(20, 22, 31, 0.72);
  border-bottom: 1px solid var(--border);
  backdrop-filter: blur(16px) saturate(140%);
  position: relative;
}
.header::after {
  content: ''; position: absolute; left: 0; right: 0; bottom: -1px; height: 1px;
  background: linear-gradient(90deg, transparent, rgba(99, 102, 241, 0.5), rgba(168, 85, 247, 0.4), transparent);
}
.logo {
  display: flex; align-items: center; gap: 8px;
  text-decoration: none; margin-right: 32px;
}
.logo-mark {
  font-size: 19px;
  filter: drop-shadow(0 0 8px rgba(99, 102, 241, 0.6));
}
.logo-word {
  font-size: 16px; font-weight: 800; letter-spacing: 0.2px;
  background: linear-gradient(135deg, #818cf8, #a855f7);
  -webkit-background-clip: text; -webkit-text-fill-color: transparent;
  background-clip: text;
}
.nav { display: flex; gap: 4px; }
.nav-link {
  padding: 6px 14px; border-radius: var(--radius-sm);
  font-size: 13px; font-weight: 500; color: var(--text-secondary);
  text-decoration: none;
  transition: all var(--duration-fast) var(--ease-out);
}
.nav-link:hover {
  color: var(--text);
  background: var(--bg-hover);
  transform: translateY(-1px);
}
.nav-link.active {
  color: #fff;
  background: var(--brand-bg);
  box-shadow: inset 0 0 0 1px rgba(99, 102, 241, 0.35), 0 0 14px rgba(99, 102, 241, 0.25);
}
.header-right {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 12px;
}
.user-name {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-secondary);
}
.logout-btn {
  padding: 4px 12px;
  border: 1px solid var(--border);
  border-radius: 6px;
  background: transparent;
  color: var(--text-secondary);
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s;
}
.logout-btn:hover {
  border-color: #f87171;
  color: #f87171;
}
</style>
