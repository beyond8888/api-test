#!/usr/bin/env python3
"""身份证正面模板 v5：按真实布局重新擦除。

【布局真相】（字符级字形确认）：
  - y616~674 = 「住址」行：标签"住址" x173~299 + 值"北京市..." x412~1133
  - y693~750 = 出生日期行：模板自带日期 → 【保留原样，不擦】（用户要求）
  - y963~1032 = 号码行：标签 x166~560 + 数字 x758~1128
    + 左侧黑点 x708~714 + 右侧残留串 x1168~1229 → 全部擦除

擦除字段：姓名值 / 性别值 / 民族值 / 住址值 / 号码行数字+黑点+尾串
保留字段：所有标签 + 出生日期行（模板原生）
"""
import os
import cv2
import numpy as np

# 基于脚本所在位置自动定位项目根目录与模板目录，项目迁移/换服务器无需改路径
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATE_DIR = os.path.join(BASE_DIR, 'frontend', 'public', 'templates')
SRC = os.path.join(TEMPLATE_DIR, 'idcard-front.png')
OUT = os.path.join(TEMPLATE_DIR, 'idcard-front-v8.png')

img = cv2.imread(SRC)
h, w = img.shape[:2]

# 擦除区（x0, y0, x1, y1）—— 边界经过保护标签校准
# 【最终布局真相】5 行：姓名/性别·民族/出生(模板自带不擦)/住址两行/号码
ERASE = [
    (349, 169, 556, 284),    # 姓名值（标签"姓名"右界300）
    (374, 318, 459, 411),    # 性别值（标签"性别"右界313）
    (728, 318, 815, 411),    # 民族值（标签"民族"右界712）
    (392, 596, 1240, 770),   # 住址两行（标签"住址"右界299 → 392 留93px保护带）
    (640, 950, 1650, 1045),  # 号码行：覆盖 x692~1580 三段连续数字
    # 出生日期行 y464~601：模板自带原生日期，【不擦】
]

mask = np.zeros((h, w), dtype=np.uint8)
for rx0, ry0, rx1, ry1 in ERASE:
    cv2.rectangle(mask, (rx0, ry0), (rx1, ry1), 255, -1)
    print(f"擦除: ({rx0},{ry0})-({rx1},{ry1})")

out = cv2.inpaint(img, mask, 9, cv2.INPAINT_TELEA)

# 双边滤波抹平痕迹
for rx0, ry0, rx1, ry1 in ERASE:
    pad = 12
    ys, ye = max(0, ry0 - pad), min(h, ry1 + pad)
    xs, xe = max(0, rx0 - pad), min(w, rx1 + pad)
    roi = out[ys:ye, xs:xe]
    out[ys:ye, xs:xe] = cv2.bilateralFilter(roi, 9, 60, 60)

cv2.imwrite(OUT, out)
print(f"\n[OK] {OUT}")

# 验证
gray = cv2.cvtColor(out, cv2.COLOR_BGR2GRAY)
print("\n=== 擦除验证 ===")
CHECKS = [
    ("姓名值", (383, 189, 522, 264)),
    ("性别值", (394, 338, 434, 391)),
    ("民族值", (748, 338, 790, 391)),
    ("住址值", (412, 616, 1133, 674)),
    ("号码黑点", (700, 963, 730, 1032)),
    ("号码数字", (738, 963, 1150, 1032)),
    ("号码尾串", (1150, 963, 1299, 1032)),
]
for label, (x0, y0, x1, y1) in CHECKS:
    n = int((gray[y0:y1 + 1, x0:x1 + 1] < 150).sum())
    print(f"  {label}: {n}", "OK" if n < 30 else "RESIDUAL!")

print("\n=== 保留验证（应完好）===")
KEEP = [
    ("姓名标签", (173, 189, 300, 264), 100),
    ("性别标签", (180, 338, 313, 391), 100),
    ("民族标签", (578, 338, 712, 391), 100),
    ("出生行(模板原生)", (500, 464, 1100, 601), 200),  # y464~601 才是真正的出生行
    ("住址标签", (173, 617, 300, 674), 100),
    ("号码标签", (166, 963, 560, 1032), 500),
]
for label, (x0, y0, x1, y1), min_n in KEEP:
    n = int((gray[y0:y1 + 1, x0:x1 + 1] < 150).sum())
    print(f"  {label}: {n}", "OK" if n >= min_n else "DAMAGED!")