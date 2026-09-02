import type { GlobalThemeOverrides } from 'naive-ui'

// Centralized dark-theme overrides for the whole app.
// Kept in sync with the design tokens defined in assets/styles/main.css so
// every Naive UI surface shares the same geometry/color language as custom CSS.
export const theme: GlobalThemeOverrides = {
  common: {
    primaryColor: '#6366f1',
    primaryColorHover: '#818cf8',
    primaryColorPressed: '#4f46e5',
    primaryColorSuppl: '#6366f1',
    borderRadius: '7px',
    fontSizeSmall: '12px',
    fontSizeMedium: '13px',
    fontSizeLarge: '14px',
  },
  Button: {
    borderRadiusSmall: '6px',
    borderRadiusMedium: '7px',
    fontWeight: '500',
    heightSmall: '30px',
    heightMedium: '34px',
  },
  Input: {
    borderRadius: '7px',
    heightSmall: '30px',
    heightMedium: '34px',
  },
  Select: {
    peers: { InternalSelection: { borderRadius: '7px', heightMedium: '34px' } },
  },
  Tabs: {
    tabTextColorActiveLine: '#818cf8',
    tabTextColorHoverLine: '#a5b0ff',
    barColor: '#6366f1',
    tabGapSmallLine: '24px',
  },
  Tag: { borderRadius: '5px' },
  // Extended coverage so every surface shares the same geometry.
  Card: { borderRadius: '11px' },
  Modal: { borderRadius: '16px' },
  Drawer: { borderRadius: '16px 0 0 16px' },
  Popover: { borderRadius: '10px' },
  Dropdown: { borderRadius: '8px' },
  Tooltip: { borderRadius: '7px' },
  Table: { borderRadius: '7px' },
  Message: { borderRadius: '8px' },
  Notification: { borderRadius: '10px' },
}
