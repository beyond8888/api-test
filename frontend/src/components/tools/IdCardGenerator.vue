<template>
  <div class="idcard-gen">
    <div class="gen-header">
      <h3>身份证、驾驶证 & 从业资格证图片生成</h3>
      <p class="gen-hint">驾驶证号、姓名与身份证保持一致，其他字段随机</p>
    </div>

    <!-- 主操作区：表单 + 按钮行 -->
    <div class="action-panel">
      <div class="form-grid">
        <div class="form-field">
          <label>姓名</label>
          <n-input v-model:value="cardData.name" placeholder="留空则随机" clearable />
        </div>
        <div class="form-field">
          <label>身份证号</label>
          <n-input v-model:value="cardData.idNumber" placeholder="留空则随机" clearable maxlength="18" />
        </div>
      </div>
      <div class="action-row">
        <n-button type="primary" :loading="drawing" @click="oneClickGenerate">
          一键生成（随机数据）
        </n-button>
        <n-button
          type="primary"
          ghost
          :disabled="!cardData.name.trim() || !cardData.idNumber.trim()"
          @click="renderCardsWithCurrentData"
        >
          用当前数据生成
        </n-button>
        <n-button class="download-all-btn" @click="downloadAll">
          一键下载全部
        </n-button>
      </div>
    </div>

    <!-- 结果预览：身份证 -->
    <div v-if="frontUrl || backUrl" class="result-section">
      <div class="result-card" v-if="frontUrl">
        <ZoomableImage :src="frontUrl" alt="身份证正面" />
        <div class="result-btns">
          <n-button size="small" @click="dlImg(frontUrl, `${cardData.name}-身份证正面.png`)">下载正面</n-button>
          <n-button size="small" @click="oneClickGenerate">换一组数据重新生成</n-button>
        </div>
      </div>
      <div class="result-card" v-if="backUrl">
        <ZoomableImage :src="backUrl" alt="身份证反面" />
        <n-button size="small" @click="dlImg(backUrl, `${cardData.name}-身份证反面.png`)">下载反面</n-button>
      </div>
    </div>

    <!-- 结果预览：驾驶证首页/副页 -->
    <div v-if="licenseResult" class="result-section">
      <div class="result-card">
        <ZoomableImage :src="licenseResult.frontUrl" alt="驾驶证首页" />
        <n-button size="small" @click="dlImg(licenseResult.frontUrl, `${cardData.name}-驾驶证首页.png`)">下载首页</n-button>
      </div>
      <div class="result-card">
        <ZoomableImage :src="licenseResult.backUrl" alt="驾驶证副页" />
        <n-button size="small" @click="dlImg(licenseResult.backUrl, `${cardData.name}-驾驶证副页.png`)">下载副页</n-button>
      </div>
    </div>

    <!-- 结果预览：从业资格证 -->
    <div v-if="qualificationResult" class="result-section result-section--single">
      <div class="result-card">
        <ZoomableImage :src="qualificationResult.url" alt="从业资格证" :max-height="300" />
        <n-button size="small" @click="dlImg(qualificationResult.url, `${cardData.name}-从业资格证.png`)">下载</n-button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { NButton, NInput, useMessage } from 'naive-ui'
import ZoomableImage from '@/components/common/ZoomableImage.vue'
import { downloadImage as dlImg } from '@/utils/canvasImage'
import { randomChineseName, randomIdNumber } from '@/utils/randomData'
import { generateFront, generateBack } from '@/composables/useIdCardCanvas'
import { generateDrivingLicense } from '@/composables/useDrivingLicenseCanvas'
import type { DrivingLicenseResult } from '@/composables/useDrivingLicenseCanvas'
import { generateQualificationCert } from '@/composables/useQualificationCertCanvas'
import type { QualificationCertResult } from '@/composables/useQualificationCertCanvas'

const message = useMessage()

// ─── 状态 ────────────────────────────────────────────────────────
const cardData = reactive({ name: '', idNumber: '' })
const frontUrl = ref('')
const backUrl = ref('')
const licenseResult = ref<DrivingLicenseResult | null>(null)
const qualificationResult = ref<QualificationCertResult | null>(null)
const drawing = ref(false)

// ─── 一键生成（核心功能） ────────────────────────────────────────
async function oneClickGenerate() {
  randomCardData()
  await renderCards()
}

async function renderCardsWithCurrentData() {
  if (!cardData.name.trim() || !cardData.idNumber.trim()) {
    message.warning('请填写姓名和身份证号，或使用「一键生成」')
    return
  }
  await renderCards()
}

async function renderCards() {
  if (!cardData.name || !cardData.idNumber) return

  drawing.value = true
  try {
    const [front, back, license, qualification] = await Promise.all([
      generateFront(cardData.name, cardData.idNumber),
      generateBack(),
      generateDrivingLicense(cardData.name, cardData.idNumber),
      generateQualificationCert(cardData.name, cardData.idNumber),
    ])
    frontUrl.value = front
    backUrl.value = back
    licenseResult.value = license
    qualificationResult.value = qualification
    message.success(`已生成：${cardData.name} / ${cardData.idNumber}`)
  } catch (e: any) {
    message.error(`生成失败：${e.message || '未知错误'}`)
  } finally {
    drawing.value = false
  }
}

// ─── 一键下载全部 ────────────────────────────────────────────────
function downloadAll() {
  const jobs: Array<{ url: string; name: string }> = []
  const tag = cardData.name || '证件'
  if (frontUrl.value) jobs.push({ url: frontUrl.value, name: `${tag}-身份证正面.png` })
  if (backUrl.value) jobs.push({ url: backUrl.value, name: `${tag}-身份证反面.png` })
  if (licenseResult.value) {
    jobs.push({ url: licenseResult.value.frontUrl, name: `${tag}-驾驶证首页.png` })
    jobs.push({ url: licenseResult.value.backUrl, name: `${tag}-驾驶证副页.png` })
  }
  if (qualificationResult.value) jobs.push({ url: qualificationResult.value.url, name: `${tag}-从业资格证.png` })
  if (!jobs.length) {
    message.warning('请先生成图片')
    return
  }
  jobs.forEach((job, i) => {
    setTimeout(() => dlImg(job.url, job.name), i * 400)
  })
  message.success(`已开始下载 ${jobs.length} 张图片`)
}

// ─── 随机数据生成（复用 @/utils/randomData 公共能力） ────────────
function randomCardData() {
  cardData.name = randomChineseName()
  cardData.idNumber = randomIdNumber()
}
</script>

<style scoped>
.idcard-gen { max-width: 920px; }
.gen-header h3 { margin: 0 0 4px; font-size: 16px; font-weight: 700; }
.gen-hint { margin: 0 0 16px; font-size: 12px; color: var(--text-muted); }

/* 主操作区（紧凑单卡片） */
.action-panel {
  padding: 16px;
  background: var(--bg-secondary);
  border: 1px solid var(--border);
  border-radius: 10px;
  margin-bottom: 16px;
}
.form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.form-field label {
  display: block; font-size: 12px; font-weight: 600;
  color: var(--text-secondary); margin-bottom: 4px;
}
.action-row { display: flex; gap: 10px; margin-top: 12px; align-items: center; }
.download-all-btn { margin-left: auto; }

/* 结果 */
.result-section { display: flex; gap: 20px; margin-bottom: 24px; }
.result-card {
  flex: 1; text-align: center;
  background: var(--bg-secondary);
  border: 1px solid var(--border); border-radius: 10px; padding: 16px;
}
.result-card h4 { font-size: 13px; margin: 0 0 10px; color: var(--text-secondary); }
.res-img { max-width: 100%; border-radius: 6px; border: 1px solid var(--border); }
/* 预览图与下方按钮保持间距 */
.result-card :deep(.zoomable-image) { margin-bottom: 10px; max-width: 100%; }
.result-card :deep(.zi-img) { margin: 0 auto; }
/* 从业资格证为竖版单张，占满整行并居中 */
.result-section--single { justify-content: center; }
.result-section--single .result-card { flex: 0 1 420px; }
.result-btns { display: flex; gap: 8px; justify-content: center; margin-top: 10px; }

@media (max-width: 700px) {
  .result-section { flex-direction: column; }
  .form-grid { grid-template-columns: 1fr; }
}
</style>
