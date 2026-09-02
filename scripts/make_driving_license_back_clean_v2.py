#!/usr/bin/env python3
"""新驾驶证副页：仅擦除证号和姓名，其他字段保持原图不变。

副页底图：frontend/public/templates/driving-license-back-src.png (1080×718)
"""
import os
import cv2
import numpy as np

# 基于脚本所在位置自动定位项目根目录与模板目录，项目迁移/换服务器无需改路径
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATE_DIR = os.path.join(BASE_DIR, 'frontend', 'public', 'templates')
SRC = os.path.join(TEMPLATE_DIR, 'driving-license-back-src.png')
OUT = os.path.join(TEMPLATE_DIR, 'driving-license-back-clean.png')

# 副页证号区 x438~889, y138~166；姓名区 x218~294, y180~240（含上下笔画/下划线）
LICENSE_BOX = (430, 134, 900, 172)
NAME_BOX = (210, 180, 305, 240)

# 逐字符擦除会漏掉的小残留，用精确小框定点清除
SPOT_FIXES = [
    (865, 145, 900, 170),   # 证号末尾的小黑点 x874~882, y154~158
    (216, 182, 300, 193),   # 姓名上方的横向残留线 y186~189, x222~292
    (210, 225, 305, 238),   # 姓名下方的虚线下划线 y229~233
]


def erase_field(img: np.ndarray, box: tuple[int, int, int, int]) -> np.ndarray:
    """逐字符擦除字段，避免整框修复阴影。"""
    h, w = img.shape[:2]
    x0, y0, x1, y1 = box

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    roi = gray[y0:y1, x0:x1]
    blur = cv2.GaussianBlur(roi, (3, 3), 0)

    # 副页文字较浅，用更低阈值确保捕获
    _, bw1 = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    _, bw2 = cv2.threshold(blur, 85, 255, cv2.THRESH_BINARY_INV)
    bw = cv2.bitwise_or(bw1, bw2)

    k = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    bw = cv2.morphologyEx(bw, cv2.MORPH_CLOSE, k, iterations=2)
    bw = cv2.morphologyEx(bw, cv2.MORPH_OPEN, k, iterations=1)

    cnts, _ = cv2.findContours(bw, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    out = img.copy()
    for c in cnts:
        cx, cy, cw, ch = cv2.boundingRect(c)
        area = cv2.contourArea(c)
        if area < 25 or ch < 10 or cw > 100:
            continue

        fx0, fy0 = x0 + cx, y0 + cy
        fx1, fy1 = fx0 + cw, fy0 + ch

        mask = np.zeros((h, w), dtype=np.uint8)
        mask[fy0:fy1, fx0:fx1] = 255
        mask = cv2.dilate(mask, k, iterations=2)
        out = cv2.inpaint(out, mask, 7, cv2.INPAINT_TELEA)

    return out


def erase_spot(img: np.ndarray, box: tuple[int, int, int, int]) -> np.ndarray:
    """定点清除小残留：整框小半径修复，区域很小不会引入阴影。"""
    h, w = img.shape[:2]
    x0, y0, x1, y1 = box
    mask = np.zeros((h, w), dtype=np.uint8)
    mask[y0:y1, x0:x1] = 255
    out = cv2.inpaint(img, mask, 9, cv2.INPAINT_TELEA)
    out = cv2.inpaint(out, mask, 5, cv2.INPAINT_TELEA)
    return out


def clean() -> None:
    img = cv2.imread(SRC)
    out = erase_field(img, LICENSE_BOX)
    out = erase_field(out, NAME_BOX)
    for box in SPOT_FIXES:
        out = erase_spot(out, box)
    cv2.imwrite(OUT, out)
    print(f"[OK] {OUT}")


if __name__ == "__main__":
    clean()
