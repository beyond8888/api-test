<script setup lang="ts">
/**
 * 可缩放预览的图片组件。
 *
 * 交互参考业界惯例（阿里云 / 腾讯云控制台、Ant Design、GitHub）：
 *  - 右下角常驻一个半透明圆形「放大镜」按钮，hover 时高亮。
 *    放在右下角而非正中，避免遮挡证件主体内容、也避免误触。
 *  - 点击按钮打开全屏预览，支持滚轮缩放、拖拽平移、按钮缩放、双击重置。
 */
import { ref } from 'vue'
import { NButton, NModal, NTooltip } from 'naive-ui'

const props = defineProps<{
  src: string
  alt?: string
  /**
   * 预览图的最大展示高度（px），仅影响页面显示，
   * 下载时使用的仍是原始 dataURL，不影响下载文件大小与清晰度。
   */
  maxHeight?: number
}>()

const MIN_SCALE = 0.5
const MAX_SCALE = 8
const SCALE_STEP = 0.25

const showPreview = ref(false)
const scale = ref(1)
const translate = ref({ x: 0, y: 0 })
const dragging = ref(false)
const dragStart = ref({ x: 0, y: 0 })

function openPreview(): void {
  showPreview.value = true
  resetZoom()
}

function resetZoom(): void {
  scale.value = 1
  translate.value = { x: 0, y: 0 }
}

function zoomIn(): void {
  scale.value = Math.min(MAX_SCALE, scale.value + SCALE_STEP)
}

function zoomOut(): void {
  scale.value = Math.max(MIN_SCALE, scale.value - SCALE_STEP)
}

/** 滚轮缩放：以光标位置为锚点效果最好，这里简化为居中缩放 */
function onWheel(e: WheelEvent): void {
  e.preventDefault()
  const delta = e.deltaY > 0 ? -0.15 : 0.15
  scale.value = Math.min(MAX_SCALE, Math.max(MIN_SCALE, scale.value + delta))
}

function onMouseDown(e: MouseEvent): void {
  dragging.value = true
  dragStart.value = {
    x: e.clientX - translate.value.x,
    y: e.clientY - translate.value.y,
  }
}

function onMouseMove(e: MouseEvent): void {
  if (!dragging.value)
    return
  translate.value = {
    x: e.clientX - dragStart.value.x,
    y: e.clientY - dragStart.value.y,
  }
}

function onMouseUp(): void {
  dragging.value = false
}
</script>

<template>
  <div class="zoomable-image">
    <img
      :src="props.src"
      :alt="props.alt || ''"
      class="zi-img"
      :style="props.maxHeight ? { maxHeight: `${props.maxHeight}px`, width: 'auto' } : undefined"
    >

    <n-tooltip trigger="hover" placement="top">
      <template #trigger>
        <button type="button" class="zi-zoom-btn" aria-label="放大查看" @click="openPreview">
          <svg viewBox="0 0 24 24" width="16" height="16" fill="none"
               stroke="currentColor" stroke-width="2" stroke-linecap="round">
            <circle cx="11" cy="11" r="7" />
            <line x1="16.5" y1="16.5" x2="21" y2="21" />
            <line x1="11" y1="8" x2="11" y2="14" />
            <line x1="8" y1="11" x2="14" y2="11" />
          </svg>
        </button>
      </template>
      点击放大查看
    </n-tooltip>

    <n-modal v-model:show="showPreview" class="zi-modal" :mask-closable="true">
      <div class="zi-preview">
        <div class="zi-toolbar">
          <n-button size="tiny" secondary @click="zoomOut">缩小</n-button>
          <span class="zi-scale">{{ Math.round(scale * 100) }}%</span>
          <n-button size="tiny" secondary @click="zoomIn">放大</n-button>
          <n-button size="tiny" secondary @click="resetZoom">重置</n-button>
          <span class="zi-tip">滚轮缩放 · 拖拽移动 · 双击复位</span>
          <n-button size="tiny" quaternary @click="showPreview = false">关闭</n-button>
        </div>

        <div
          class="zi-body"
          :class="{ 'is-dragging': dragging }"
          @wheel.prevent="onWheel"
          @mousedown="onMouseDown"
          @mousemove="onMouseMove"
          @mouseup="onMouseUp"
          @mouseleave="onMouseUp"
        >
          <img
            :src="props.src"
            :alt="props.alt || ''"
            class="zi-preview-img"
            :style="{ transform: `translate(${translate.x}px, ${translate.y}px) scale(${scale})` }"
            @dblclick="resetZoom"
            @click.stop
          >
        </div>
      </div>
    </n-modal>
  </div>
</template>

<style scoped>
.zoomable-image {
  position: relative;
  display: inline-block;
  max-width: 100%;
}

.zi-img {
  display: block;
  max-width: 100%;
  border-radius: 6px;
  border: 1px solid var(--border, rgba(0, 0, 0, 0.12));
}

/* 右下角悬浮放大按钮：不遮挡证件主体，避免误触 */
.zi-zoom-btn {
  position: absolute;
  right: 8px;
  bottom: 8px;
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0;
  border: none;
  border-radius: 50%;
  cursor: pointer;
  color: #fff;
  background: rgba(0, 0, 0, 0.45);
  backdrop-filter: blur(2px);
  opacity: 0.75;
  transition: opacity 0.15s, background 0.15s, transform 0.15s;
}

.zoomable-image:hover .zi-zoom-btn {
  opacity: 1;
}

.zi-zoom-btn:hover {
  background: rgba(0, 0, 0, 0.7);
  transform: scale(1.08);
}

.zi-zoom-btn:active {
  transform: scale(0.96);
}

/* ─── 预览弹层 ─── */
.zi-preview {
  display: flex;
  flex-direction: column;
  width: 92vw;
  height: 92vh;
  background: var(--bg-secondary, #ffffff);
  border-radius: 10px;
  overflow: hidden;
}

.zi-toolbar {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
  border-bottom: 1px solid var(--border, rgba(0, 0, 0, 0.1));
  flex-shrink: 0;
}

.zi-scale {
  min-width: 48px;
  text-align: center;
  font-size: 12px;
  font-variant-numeric: tabular-nums;
  color: var(--text-secondary, #666);
}

.zi-tip {
  margin-left: auto;
  font-size: 12px;
  color: var(--text-muted, #999);
}

.zi-body {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  cursor: grab;
  /* 深色纯背景：突出证件主体，取代原棋盘格纹理 */
  background: #212121;
}

.zi-body.is-dragging {
  cursor: grabbing;
}

.zi-preview-img {
  max-width: 100%;
  max-height: 100%;
  object-fit: contain;
  transition: transform 0.08s linear;
  user-select: none;
  -webkit-user-drag: none;
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.18);
}

@media (max-width: 700px) {
  .zi-tip { display: none; }
}
</style>
