#!/usr/bin/env python3
"""机动车行驶证副页：擦除号牌号码与档案编号，其他字段保持原图不变。

底图：frontend/public/templates/vehicle-license-back-src.png (1080×769)
"""
import os
import cv2
import numpy as np

# 基于脚本所在位置自动定位项目根目录与模板目录，项目迁移/换服务器无需改路径
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATE_DIR = os.path.join(BASE_DIR, 'frontend', 'public', 'templates')
SRC = os.path.join(TEMPLATE_DIR, 'vehicle-license-back-src.png')
OUT = os.path.join(TEMPLATE_DIR, 'vehicle-license-back-clean.png')

# 号牌号码区域（实测：青JZ373R → x254~439, y84~125）
# 左侧 x110~220 为字段标签，不可误擦
PLATE_BOX = (240, 80, 450, 130)

# 档案编号区域（实测：12 位数字 x644~902, y91~117）
# 左侧 x470~590 为"档案编号"标签，不可误擦
ARCHIVE_BOX = (635, 85, 915, 125)

# 检验有效期至日期区域（实测：2040年06月 → x520~770, y515~570）
# 左侧 x250~505 为"检验有效期至"标签，右侧 x770~840 为"豫A"印章，均需保留
INSPECTION_DATE_BOX = (515, 508, 775, 575)


def erase_box(img: np.ndarray, box: tuple) -> np.ndarray:
    """逐字符精确 mask + 小半径 inpaint 方案擦除区域文字。"""
    x0, y0, x1, y1 = box

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    roi = gray[y0:y1, x0:x1]
    blur = cv2.GaussianBlur(roi, (3, 3), 0)

    # 二值化：OTSU + 低阈值，确保完整字符
    _, bw1 = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    _, bw2 = cv2.threshold(blur, 110, 255, cv2.THRESH_BINARY_INV)
    bw = cv2.bitwise_or(bw1, bw2)

    k = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    bw = cv2.morphologyEx(bw, cv2.MORPH_CLOSE, k, iterations=1)
    bw = cv2.morphologyEx(bw, cv2.MORPH_OPEN, k, iterations=1)

    cnts, _ = cv2.findContours(bw, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # 合并所有字符 mask，一次修复
    mask = np.zeros(img.shape[:2], dtype=np.uint8)
    for c in cnts:
        cx, cy, cw, ch = cv2.boundingRect(c)
        area = cv2.contourArea(c)
        # 过滤噪声与横线
        if area < 80 or ch < 12 or cw > 200:
            continue
        fx0, fy0 = x0 + cx, y0 + cy
        fx1, fy1 = fx0 + cw, fy0 + ch
        mask[fy0:fy1, fx0:fx1] = 255

    # 轻微膨胀覆盖边缘
    mask = cv2.dilate(mask, k, iterations=1)

    # 小半径修复（仅参考紧邻像素，保留纹理，避免阴影/色块）
    out = cv2.inpaint(img, mask, 7, cv2.INPAINT_TELEA)
    return out


def clean() -> None:
    img = cv2.imread(SRC)
    out = erase_box(img, PLATE_BOX)
    out = erase_box(out, ARCHIVE_BOX)
    out = erase_box(out, INSPECTION_DATE_BOX)
    cv2.imwrite(OUT, out)
    print(f"[OK] {OUT}")


if __name__ == "__main__":
    clean()
