<template>
  <div class="login-page">
    <div class="login-container">
      <!-- 品牌侧边栏（宽屏显示） -->
      <aside class="login-aside">
        <div class="aside-brand">
          <div class="aside-logo">API</div>
          <h2>API Test Platform</h2>
          <p>简洁、高效的接口测试工作台<br />让接口调试与协作更轻松</p>
        </div>
        <ul class="aside-features">
          <li>多环境一键切换</li>
          <li>接口集合与历史管理</li>
          <li>可视化请求编排</li>
        </ul>
        <div class="aside-footer">© 2026 API Test Platform</div>
      </aside>

      <!-- 表单区：与全站一致的暗色主题 -->
      <div class="login-form-wrap">
        <div class="login-header">
            <div class="login-logo">API</div>
            <h1>欢迎使用</h1>
            <p>{{ isRegister ? '创建新账号' : '登录到你的账号' }}</p>
          </div>

          <n-tabs v-model:value="activeTab" type="segment" size="large">
            <n-tab-pane name="login" tab="登录">
              <n-form :model="loginForm" :rules="loginRules" label-placement="top">
                <n-form-item path="username" label="用户名">
                  <n-input v-model:value="loginForm.username" placeholder="输入用户名" @keyup.enter="handleLogin" />
                </n-form-item>
                <n-form-item path="password" label="密码">
                  <n-input v-model:value="loginForm.password" type="password" show-password-on="click"
                    placeholder="输入密码" @keyup.enter="handleLogin" />
                </n-form-item>
                <n-button type="primary" block size="large" :loading="loading" @click="handleLogin">
                  登录
                </n-button>
              </n-form>
            </n-tab-pane>

            <n-tab-pane name="register" tab="注册">
              <n-form :model="registerForm" :rules="registerRules" label-placement="top">
                <n-form-item path="username" label="用户名">
                  <n-input v-model:value="registerForm.username" placeholder="3-64 个字符" />
                </n-form-item>
                <n-form-item path="password" label="密码">
                  <n-input v-model:value="registerForm.password" type="password" show-password-on="click"
                    placeholder="至少 8 位，含字母和数字" />
                </n-form-item>
                <n-form-item path="confirmPassword" label="确认密码">
                  <n-input v-model:value="registerForm.confirmPassword" type="password" show-password-on="click"
                    placeholder="再次输入密码" @keyup.enter="handleRegister" />
                </n-form-item>
                <n-button type="primary" block size="large" :loading="loading" @click="handleRegister">
                  注册
                </n-button>
              </n-form>
            </n-tab-pane>
          </n-tabs>

          <div v-if="errorMsg" class="login-error">{{ errorMsg }}</div>
        </div>
      </div>
    </div>
</template>

<script setup lang="ts">
import { ref, reactive, watch } from 'vue'
import { useRouter } from 'vue-router'
import {
  NForm, NFormItem, NInput, NButton, NTabs, NTabPane,
  useMessage, type FormRules,
} from 'naive-ui'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const message = useMessage()
const authStore = useAuthStore()

const loading = ref(false)
const errorMsg = ref('')
const activeTab = ref('login')
const isRegister = ref(false)

watch(activeTab, (v) => { isRegister.value = v === 'register'; errorMsg.value = '' })

const loginForm = reactive({ username: '', password: '' })
const registerForm = reactive({ username: '', password: '', confirmPassword: '' })

const loginRules: FormRules = {
  username: { required: true, message: '请输入用户名', trigger: 'blur' },
  password: { required: true, message: '请输入密码', trigger: 'blur' },
}

const registerRules: FormRules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, message: '至少 3 个字符', trigger: 'blur' },
    { max: 64, message: '最多 64 个字符', trigger: 'blur' },
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 8, message: '至少 8 个字符', trigger: 'blur' },
    {
      validator: (_r: any, v: string) => /[A-Za-z]/.test(v) && /\d/.test(v),
      message: '需同时包含字母和数字',
      trigger: 'blur',
    },
  ],
  confirmPassword: [
    { required: true, message: '请确认密码', trigger: 'blur' },
    {
      validator: (_r: any, v: string) => v === registerForm.password,
      message: '两次密码不一致',
      trigger: 'blur',
    },
  ],
}

async function handleLogin() {
  if (!loginForm.username || !loginForm.password) {
    errorMsg.value = '请填写用户名和密码'
    return
  }
  loading.value = true
  errorMsg.value = ''
  try {
    await authStore.login(loginForm.username, loginForm.password)
    message.success('登录成功')
    router.push('/')
  } catch (e: any) {
    errorMsg.value =
      e?.response?.data?.message ||
      e?.response?.data?.detail ||
      e?.message ||
      '登录失败'
  } finally {
    loading.value = false
  }
}

async function handleRegister() {
  if (registerForm.password !== registerForm.confirmPassword) {
    errorMsg.value = '两次密码不一致'
    return
  }
  loading.value = true
  errorMsg.value = ''
  try {
    await authStore.register(registerForm.username, registerForm.password)
    message.success('注册成功，已自动登录')
    router.push('/')
  } catch (e: any) {
    const data = e?.response?.data
    errorMsg.value = data?.username?.[0] || data?.message || e?.message || '注册失败'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  box-sizing: border-box;
  background:
    radial-gradient(1000px circle at 12% -8%, rgba(99, 102, 241, 0.13), transparent 42%),
    radial-gradient(900px circle at 100% 0%, rgba(168, 85, 247, 0.08), transparent 40%),
    var(--bg-root);
}
.login-container {
  width: 100%;
  max-width: 920px;
  display: flex;
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 18px;
  overflow: hidden;
  box-shadow: var(--shadow-md);
  min-height: 540px;
}

/* 品牌侧边栏 */
.login-aside {
  flex: 1 1 45%;
  background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 55%, #7c3aed 100%);
  color: #fff;
  padding: 40px 36px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
}
.aside-logo {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 60px;
  height: 60px;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.18);
  font-weight: 800;
  font-size: 20px;
  letter-spacing: 0.5px;
  margin-bottom: 18px;
}
.aside-brand h2 {
  font-size: 24px;
  font-weight: 700;
  margin: 0 0 10px;
}
.aside-brand p {
  font-size: 14px;
  opacity: 0.85;
  margin: 0;
  line-height: 1.6;
}
.aside-features {
  list-style: none;
  padding: 0;
  margin: 0;
}
.aside-features li {
  font-size: 14px;
  opacity: 0.92;
  margin: 14px 0;
  padding-left: 28px;
  position: relative;
}
.aside-features li::before {
  content: '';
  position: absolute;
  left: 0;
  top: 4px;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.25);
}
.aside-footer {
  font-size: 12px;
  opacity: 0.7;
}

/* 表单区 */
.login-form-wrap {
  flex: 1 1 55%;
  padding: 44px 40px;
  display: flex;
  flex-direction: column;
  justify-content: center;
}
.login-header {
  text-align: center;
  margin-bottom: 26px;
}
.login-logo {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 52px;
  height: 52px;
  border-radius: 14px;
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
  color: #fff;
  font-weight: 800;
  font-size: 16px;
  margin-bottom: 14px;
}
.login-header h1 {
  font-size: 22px;
  font-weight: 700;
  margin: 0 0 6px;
  color: var(--text);
}
.login-header p {
  font-size: 13px;
  color: var(--text-secondary);
  margin: 0;
}
.login-error {
  margin-top: 18px;
  padding: 10px 14px;
  background: var(--error-bg);
  border: 1px solid rgba(248, 113, 113, 0.35);
  border-radius: 8px;
  color: var(--error);
  font-size: 13px;
  text-align: center;
}

@media (max-width: 720px) {
  .login-container {
    flex-direction: column;
    min-height: auto;
    max-width: 420px;
  }
  .login-aside {
    display: none;
  }
  .login-form-wrap {
    padding: 36px 28px;
  }
}
</style>
