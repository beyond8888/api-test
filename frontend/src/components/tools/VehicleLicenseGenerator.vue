<template>
  <div class="vehicle-license-gen">
    <div class="gen-header">
      <h3>行驶证 · 道运 · 人车合影</h3>
      <p class="gen-hint">一键同时生成行驶证正页、副页、道路运输证主页与人车合影，车牌号四处一致，支持手动输入或随机生成</p>
    </div>

    <!-- 主操作区 -->
    <div class="action-panel">
      <div class="form-grid">
        <div class="form-field">
          <label>车牌号</label>
          <n-input
            v-model:value="plateNo"
            placeholder="留空则随机，如 京A12345"
            clearable
            maxlength="10"
          />
        </div>
        <div class="form-field">
          <label>车辆识别代号（VIN）</label>
          <n-input
            v-model:value="vin"
            placeholder="留空则随机，17 位大写字母/数字"
            clearable
            maxlength="17"
          />
        </div>
        <div class="form-field">
          <label>发动机号码</label>
          <n-input
            v-model:value="engineNo"
            placeholder="留空则随机，8~12 位大写字母/数字"
            clearable
            maxlength="12"
          />
        </div>
        <div class="form-field">
          <label>档案编号</label>
          <n-input
            v-model:value="archiveNo"
            placeholder="留空则随机，12 位数字"
            clearable
            maxlength="12"
          />
        </div>
        <div class="form-field">
          <label>经营许可证号</label>
          <n-input
            v-model:value="licenseNo"
            placeholder="留空则随机，12 位数字"
            clearable
            maxlength="12"
          />
        </div>
        <div class="form-field">
          <label>道路运输证号</label>
          <n-input
            v-model:value="certificateNo"
            placeholder="留空则随机，如 云交运管昆字530102797211号"
            clearable
            maxlength="25"
          />
        </div>
        <div class="form-field wide">
          <label>检验有效期至</label>
          <n-input
            v-model:value="inspectionDate"
            placeholder="格式 YYYY年MM月，留空则取当前+15个月"
            clearable
            maxlength="12"
          />
        </div>
      </div>
      <div class="action-row">
        <n-button type="primary" :loading="drawing" @click="oneClickGenerate">
          一键生成（全部随机）
        </n-button>
        <n-button
          type="primary"
          ghost
          :disabled="!plateNo.trim()"
          @click="renderWithCurrent"
        >
          用当前值生成
        </n-button>
        <n-button class="download-all-btn" @click="downloadAll">
          一键下载全部
        </n-button>
      </div>
    </div>

    <!-- 结果预览 -->
    <div v-if="result || backResult || roadResult" class="result-section">
      <div v-if="result" class="result-card">
        <ZoomableImage :src="result.url" alt="行驶证正页" />
        <div class="result-btns">
          <n-button size="small" @click="dlImg(result.url, `${plateNo}-行驶证正页.png`)">下载正页</n-button>
        </div>
      </div>
      <div v-if="backResult" class="result-card">
        <ZoomableImage :src="backResult.url" alt="行驶证副页" />
        <div class="result-btns">
          <n-button size="small" @click="dlImg(backResult.url, `${plateNo}-行驶证副页.png`)">下载副页</n-button>
        </div>
      </div>
      <div v-if="roadResult" class="result-card">
        <ZoomableImage :src="roadResult.url" alt="道路运输证主页" />
        <div class="result-btns">
          <n-button size="small" @click="dlImg(roadResult.url, `${plateNo}-道路运输证主页.png`)">下载道路运输证</n-button>
        </div>
      </div>
      <div class="result-card">
        <ZoomableImage v-if="personPreview" :src="personPreview" alt="人车合影" />
        <div v-else class="person-status">{{ personError || '等待生成' }}</div>
        <canvas ref="personCanvas" class="hidden-canvas" />
        <div class="result-btns">
          <n-button size="small" :disabled="!plateNo.trim()" @click="downloadPerson()">下载人车合影</n-button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted } from 'vue'
import { NButton, NInput, useMessage } from 'naive-ui'
import ZoomableImage from '@/components/common/ZoomableImage.vue'
import { downloadImage as dlImg } from '@/utils/canvasImage'
import { usePersonCarPhotoCanvas } from '@/composables/usePersonCarPhotoCanvas'
import {
  randomPlateNo, randomVIN, randomEngineNo, randomArchiveNo, randomLicenseNo,
} from '@/utils/randomData'
import { generateVehicleLicense } from '@/composables/useVehicleLicenseCanvas'
import type { VehicleLicenseResult } from '@/composables/useVehicleLicenseCanvas'
import { generateVehicleLicenseBack, formatInspectionDate } from '@/composables/useVehicleLicenseBackCanvas'
import type { VehicleLicenseBackResult } from '@/composables/useVehicleLicenseBackCanvas'
import { generateRoadTransport, randomCertificateNo } from '@/composables/useRoadTransportCanvas'
import type { RoadTransportResult } from '@/composables/useRoadTransportCanvas'

const message = useMessage()
const PERSON_TEMPLATE_SRC = '/templates/person-car-photo-clean.png?v=3'

const plateNo = ref('')
const vin = ref('')
const engineNo = ref('')
const archiveNo = ref('')
const licenseNo = ref('')
const certificateNo = ref('')
const inspectionDate = ref(formatInspectionDate())
const result = ref<VehicleLicenseResult | null>(null)
const backResult = ref<VehicleLicenseBackResult | null>(null)
const roadResult = ref<RoadTransportResult | null>(null)
const drawing = ref(false)

// 人车合影：复用公共 canvas composable，车牌与行驶证/道运共享
const {
  canvas: personCanvas,
  loading: personLoading,
  error: personError,
  options: personOptions,
  loadTemplate: loadPersonTemplate,
  download: downloadPerson,
} = usePersonCarPhotoCanvas()

// canvas 快照：重绘后导出 dataURL 供 ZoomableImage 预览（同时获得放大效果）
const personPreview = ref('')
watch([personCanvas, personOptions], () => {
  requestAnimationFrame(() => {
    const cvs = personCanvas.value
    if (!cvs || !cvs.width) return
    personPreview.value = cvs.toDataURL('image/png')
  })
}, { deep: true })

onMounted(() => {
  loadPersonTemplate(PERSON_TEMPLATE_SRC).catch(() => {/* error handled inside */})
})

async function oneClickGenerate() {
  plateNo.value = randomPlateNo()
  vin.value = randomVIN()
  engineNo.value = randomEngineNo()
  archiveNo.value = randomArchiveNo()
  licenseNo.value = randomLicenseNo()
  certificateNo.value = randomCertificateNo()
  inspectionDate.value = formatInspectionDate()
  await render()
}

async function renderWithCurrent() {
  if (!plateNo.value.trim()) {
    message.warning('请填写车牌号，或使用「一键生成」')
    return
  }
  await render()
}

/** 一键下载全部：收集已生成的图片，逐个间隔触发下载避免浏览器拦截 */
function downloadAll() {
  const jobs: Array<{ url: string; name: string }> = []
  if (result.value) jobs.push({ url: result.value.url, name: `${plateNo.value}-行驶证正页.png` })
  if (backResult.value) jobs.push({ url: backResult.value.url, name: `${plateNo.value}-行驶证副页.png` })
  if (roadResult.value) jobs.push({ url: roadResult.value.url, name: `${plateNo.value}-道路运输证主页.png` })
  if (personPreview.value) jobs.push({ url: personPreview.value, name: `${plateNo.value}-人车合影.png` })
  if (!jobs.length) {
    message.warning('请先生成图片')
    return
  }
  jobs.forEach((job, i) => {
    setTimeout(() => dlImg(job.url, job.name), i * 400)
  })
  message.success(`已开始下载 ${jobs.length} 张图片`)
}

async function render() {
  if (!plateNo.value.trim()) return

  drawing.value = true
  try {
    // 留空时自动随机（模板已擦除这些字段，必须写入），并回写状态保持标题一致
    if (!vin.value.trim()) vin.value = randomVIN()
    if (!engineNo.value.trim()) engineNo.value = randomEngineNo()
    if (!archiveNo.value.trim()) archiveNo.value = randomArchiveNo()
    if (!licenseNo.value.trim()) licenseNo.value = randomLicenseNo()
    if (!certificateNo.value.trim()) certificateNo.value = randomCertificateNo()
    if (!inspectionDate.value.trim()) inspectionDate.value = formatInspectionDate()
    result.value = await generateVehicleLicense(plateNo.value, vin.value, engineNo.value)
    backResult.value = await generateVehicleLicenseBack(plateNo.value, archiveNo.value, inspectionDate.value)
    roadResult.value = await generateRoadTransport(plateNo.value, licenseNo.value, certificateNo.value)
    // 同步人车合影车牌（composable 内部 watch 自动重绘）
    personOptions.value.number = plateNo.value
    message.success(`已生成证件：${plateNo.value}`)
  } catch (e: any) {
    message.error(`生成失败：${e.message || '未知错误'}`)
  } finally {
    drawing.value = false
  }
}
</script>

<style scoped>
.vehicle-license-gen { max-width: 920px; }
.gen-header h3 { margin: 0 0 4px; font-size: 16px; font-weight: 700; }
.gen-hint { margin: 0 0 16px; font-size: 12px; color: var(--text-muted); }

.action-panel {
  padding: 16px;
  background: var(--bg-secondary);
  border: 1px solid var(--border);
  border-radius: 10px;
  margin-bottom: 16px;
}
.form-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px; }
.form-field label {
  display: block; font-size: 12px; font-weight: 600;
  color: var(--text-secondary); margin-bottom: 4px;
}
.form-field.wide { grid-column: 1 / -1; }
.action-row { display: flex; gap: 10px; margin-top: 12px; align-items: center; }
.download-all-btn { margin-left: auto; }

.result-section {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 20px;
  margin-bottom: 24px;
}
.result-card {
  text-align: center;
  background: var(--bg-secondary);
  border: 1px solid var(--border); border-radius: 10px; padding: 16px;
}
.result-card :deep(.zoomable-image) { margin-bottom: 10px; max-width: 100%; }
.result-card :deep(.zi-img) { margin: 0 auto; }
.hidden-canvas { display: none; }
.person-status {
  min-height: 160px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #999;
  font-size: 13px;
}
.result-btns { display: flex; gap: 8px; justify-content: center; margin-top: 10px; }

@media (max-width: 700px) {
  .form-grid { grid-template-columns: 1fr; }
  .result-section { grid-template-columns: 1fr; }
}
</style>
