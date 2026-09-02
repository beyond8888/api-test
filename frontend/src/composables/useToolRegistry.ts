import type { ToolDef, ToolCategory } from '@/types/tools'
import { defineAsyncComponent } from 'vue'

export const toolCategories: ToolCategory[] = [
  { key: 'generator', label: '数据生成器', icon: 'sparkles' },
  { key: 'mq',        label: '消息队列',   icon: 'send' },
]

export const toolRegistry: ToolDef[] = [
  {
    id: 'idcard',
    name: '身份证/驾驶证图片生成',
    desc: '生成带水印的身份证正反面及驾驶证图片，驾驶证号与身份证保持一致',
    icon: 'idcard',
    category: 'generator',
    component: defineAsyncComponent(() => import('@/components/tools/IdCardGenerator.vue')),
  },
  {
    id: 'vehicle-license',
    name: '行驶证 · 道运 · 人车合影',
    desc: '一键生成行驶证正页/副页、道路运输证主页与人车合影，车牌号四处一致，支持随机生成车牌号、VIN、发动机号码等',
    icon: 'vehicle-license',
    category: 'generator',
    component: defineAsyncComponent(() => import('@/components/tools/VehicleLicenseGenerator.vue')),
  },
  {
    id: 'kafka',
    name: 'Kafka 消息发送',
    desc: '向 Kafka Topic 发送测试消息',
    icon: 'kafka',
    category: 'mq',
    component: defineAsyncComponent(() => import('@/components/tools/KafkaSender.vue')),
  },
  {
    id: 'rocketmq',
    name: 'RocketMQ 消息发送',
    desc: '向阿里云 RocketMQ 5.x 发送测试消息（普通/顺序/延时）',
    icon: 'rocketmq',
    category: 'mq',
    component: defineAsyncComponent(() => import('@/components/tools/RocketMQSender.vue')),
  },
]

export function getToolsByCategory(catKey: string): ToolDef[] {
  return toolRegistry.filter(t => t.category === catKey)
}
