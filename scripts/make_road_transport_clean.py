"""生成道路运输证主页干净模板：只擦除车牌号码值区"""
import os
import sys
import cv2
import numpy as np

# 基于脚本所在位置自动定位项目根目录与模板目录，项目迁移/换服务器无需改路径
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATE_DIR = os.path.join(BASE_DIR, 'frontend', 'public', 'templates')
SRC = os.path.join(TEMPLATE_DIR, 'road-transport-src.png')
DST = os.path.join(TEMPLATE_DIR, 'road-transport-clean.png')

# 车牌号码值区：原图 "青JZ373R"，OCR y=450 行，值 x261~361、y450~474
PLATE_BOX = (255, 445, 370, 480)
# 经营许可证号值区：原图 "337374899868"，值 x261~428、y487~503
LICENSE_BOX = (256, 480, 435, 510)
# 道路运输证号整行：原图 "交运管 字 号" 在 y255~286，x300~720
CERT_LINE_BOX = (300, 255, 720, 286)

def main():
    img = cv2.imread(SRC, cv2.IMREAD_UNCHANGED)
    if img is None:
        print(f"无法读取 {SRC}", file=sys.stderr)
        sys.exit(1)

    # 统一转 BGR
    if img.shape[2] == 4:
        bgr = img[:, :, :3]
        alpha = img[:, :, 3]
    else:
        bgr = img
        alpha = None

    mask = np.zeros(bgr.shape[:2], dtype=np.uint8)
    for x1, y1, x2, y2 in (PLATE_BOX, LICENSE_BOX, CERT_LINE_BOX):
        mask[y1:y2, x1:x2] = 255

    cleaned = cv2.inpaint(bgr, mask, 3, cv2.INPAINT_TELEA)

    if alpha is not None:
        cleaned = cv2.merge([cleaned, alpha])

    cv2.imwrite(DST, cleaned)
    print(f"已生成干净模板：{DST}")

if __name__ == "__main__":
    main()
