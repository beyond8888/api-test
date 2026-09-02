#!/usr/bin/env python3
"""道路运输从业资格证：仅擦除姓名和证号，其他字段保持原图不变。

底图：frontend/public/templates/qualification-cert-src.png (1152×1620)
"""
import os
import cv2
import numpy as np

# 基于脚本所在位置自动定位项目根目录与模板目录，项目迁移/换服务器无需改路径
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATE_DIR = os.path.join(BASE_DIR, 'frontend', 'public', 'templates')
SRC = os.path.join(TEMPLATE_DIR, 'qualification-cert-src.png')
OUT = os.path.join(TEMPLATE_DIR, 'qualification-cert-clean.png')

# 姓名区、证号值区域（基于元秀-从业资格证.png 1152×1620 标定）
NAME_BOX = (355, 478, 470, 540)
LICENSE_BOX = (380, 805, 870, 850)

# 逐字符擦除后仍残留的细线/断笔，用精确小框定点清除
NAME_SPOT_FIXES = [
    (360, 486, 470, 500),   # 姓名上侧横线残留 y492~494
    (360, 518, 470, 532),   # 姓名下侧残留 y523~526
]


def erase_field(img: np.ndarray, box: tuple[int, int, int, int]) -> np.ndarray:
    """从业资格证背景为纯白+浅色水印，适合用采样背景色填充。"""
    h, w = img.shape[:2]
    x0, y0, x1, y1 = box

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    roi = gray[y0:y1, x0:x1]
    blur = cv2.GaussianBlur(roi, (3, 3), 0)

    _, bw1 = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    _, bw2 = cv2.threshold(blur, 110, 255, cv2.THRESH_BINARY_INV)
    bw = cv2.bitwise_or(bw1, bw2)

    k = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    bw = cv2.morphologyEx(bw, cv2.MORPH_CLOSE, k, iterations=1)
    bw = cv2.morphologyEx(bw, cv2.MORPH_OPEN, k, iterations=1)

    cnts, _ = cv2.findContours(bw, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    out = img.copy().astype(np.float32)

    for c in cnts:
        cx, cy, cw, ch = cv2.boundingRect(c)
        area = cv2.contourArea(c)
        if area < 35 or ch < 10 or cw > 200:
            continue

        fx0, fy0 = x0 + cx, y0 + cy
        fx1, fy1 = fx0 + cw, fy0 + ch

        # 用当前框外环采样背景色，避免水印/文字污染
        pad = 10
        sy0, sy1 = max(0, fy0 - pad), min(h, fy1 + pad)
        sx0, sx1 = max(0, fx0 - pad), min(w, fx1 + pad)
        border = np.concatenate([
            out[sy0:fy0, sx0:sx1].reshape(-1, 3),
            out[fy1:sy1, sx0:sx1].reshape(-1, 3),
            out[fy0:fy1, sx0:fx0].reshape(-1, 3),
            out[fy0:fy1, fx1:sx1].reshape(-1, 3),
        ])
        if border.shape[0] == 0:
            continue
        mean_color = np.median(border, axis=0)

        # 创建稍大的 mask 覆盖文字
        mask = np.zeros((h, w), dtype=np.uint8)
        mask[fy0:fy1, fx0:fx1] = 255
        mask = cv2.dilate(mask, k, iterations=2)
        out[mask > 0] = mean_color

    # 小半径高斯模糊平滑边界
    pad = 5
    ys, ye = max(0, y0 - pad), min(h, y1 + pad)
    xs, xe = max(0, x0 - pad), min(w, x1 + pad)
    roi_smooth = out[ys:ye, xs:xe]
    out[ys:ye, xs:xe] = cv2.GaussianBlur(roi_smooth, (5, 5), 0)

    return np.clip(out, 0, 255).astype(np.uint8)


def erase_spot(img: np.ndarray, box: tuple[int, int, int, int]) -> np.ndarray:
    """定点清除小残留：用外环背景色填充后轻微模糊。"""
    h, w = img.shape[:2]
    x0, y0, x1, y1 = box

    # 外环采样背景色
    pad = 12
    sy0, sy1 = max(0, y0 - pad), min(h, y1 + pad)
    sx0, sx1 = max(0, x0 - pad), min(w, x1 + pad)
    border = np.concatenate([
        img[sy0:y0, sx0:sx1].reshape(-1, 3),
        img[y1:sy1, sx0:sx1].reshape(-1, 3),
        img[y0:y1, sx0:x0].reshape(-1, 3),
        img[y0:y1, x1:sx1].reshape(-1, 3),
    ])
    if border.shape[0] == 0:
        return img
    mean_color = np.median(border, axis=0)

    out = img.astype(np.float32)
    out[y0:y1, x0:x1] = mean_color
    # 轻微模糊平滑
    roi = out[y0:y1, x0:x1]
    out[y0:y1, x0:x1] = cv2.GaussianBlur(roi, (5, 5), 0)
    return np.clip(out, 0, 255).astype(np.uint8)


def clean() -> None:
    img = cv2.imread(SRC)
    out = erase_field(img, NAME_BOX)
    out = erase_field(out, LICENSE_BOX)
    for box in NAME_SPOT_FIXES:
        out = erase_spot(out, box)
    cv2.imwrite(OUT, out)
    print(f"[OK] {OUT}")


if __name__ == "__main__":
    clean()
