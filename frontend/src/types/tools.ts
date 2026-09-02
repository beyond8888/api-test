import type { Component } from 'vue'

export interface ToolCategory {
  key: string
  label: string
  icon: string   // SVG path or icon name
}

export interface ToolDef {
  id: string
  name: string
  desc: string
  icon: string   // SVG markup string
  category: string
  component: Component
}
