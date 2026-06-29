"""
批量将文件夹内的 PDF / WebP / PNG / BMP / TIFF 等格式转换为 JPG，
自动适配 iPad Pro 12.9" (2732×2048) 分辨率：大图等比缩小，小图分步放大并锐化。
PDF 动态渲染至足够像素再缩放到目标尺寸，确保清晰度。
用法：直接运行，粘贴目标文件夹路径即可。
"""

import os
import sys
import math
from pathlib import Path

try:
    from PIL import Image, ImageFilter
except ImportError:
    print("错误：缺少 Pillow 库，请先安装：pip install pillow")
    sys.exit(1)

try:
    import pypdfium2 as pdfium
    HAS_PDF = True
except ImportError:
    HAS_PDF = False

# ========== 配置 ==========
IMG_EXTENSIONS = {".webp", ".png", ".bmp", ".tiff", ".tif", ".avif", ".heic", ".heif", ".jpeg", ".jfif"}
OUTPUT_QUALITY = 95         # JPG 质量 (1-100)

# --- iPad Pro 12.9" 适配 ---
TARGET_W = 2732             # iPad 横向像素
TARGET_H = 2048             # iPad 纵向像素
MIN_LONG_SIDE = 2200        # 小图放大目标长边（低于此值触发放大）
UPSCALE_STEP = 1.5          # 分步放大倍率上限（超过此值分多步）
STEP_SHARPEN_RADIUS = 0.6   # 步间轻锐化半径

SHARPEN_ENABLED = True      # 最终锐化开关
SHARPEN_RADIUS = 1.2        # 最终锐化半径
SHARPEN_PERCENT = 100       # 最终锐化强度
SHARPEN_THRESHOLD = 2       # 噪声阈值

DELETE_ORIGINAL = False     # 是否删除原文件（谨慎使用）


def _long_side(w: int, h: int) -> int:
    return max(w, h)


def _short_side(w: int, h: int) -> int:
    return min(w, h)


def _fit_scale(w: int, h: int, max_w: int, max_h: int) -> float:
    """计算等比缩放至不超出 max_w×max_h 所需的比例（≤1）。"""
    return min(max_w / w, max_h / h, 1.0)


def sharpen(img: Image.Image, radius: float = None, percent: float = None,
            threshold: float = None) -> Image.Image:
    """Unsharp Mask 锐化。可覆盖默认参数用于步间轻锐化。"""
    if not SHARPEN_ENABLED and radius is None:
        return img
    return img.filter(ImageFilter.UnsharpMask(
        radius=radius if radius is not None else SHARPEN_RADIUS,
        percent=percent if percent is not None else SHARPEN_PERCENT,
        threshold=threshold if threshold is not None else SHARPEN_THRESHOLD,
    ))


def resize_for_ipad(img: Image.Image) -> Image.Image:
    """
    将图片调整至适合 iPad Pro 12.9" 的尺寸：
    - 大图等比缩小至 2732×2048 以内
    - 小图分步放大至长边 ≥ 2200px，步间轻锐化
    - 中等尺寸不缩放
    """
    w, h = img.size

    # --- 大图缩小 ---
    if w > TARGET_W or h > TARGET_H:
        scale = _fit_scale(w, h, TARGET_W, TARGET_H)
        new_w, new_h = int(w * scale), int(h * scale)
        print(f"  (缩小 {w}×{h} → {new_w}×{new_h})", end="")
        return img.resize((new_w, new_h), Image.LANCZOS)

    # --- 小图放大 ---
    long = _long_side(w, h)
    if long < MIN_LONG_SIDE:
        target_scale = MIN_LONG_SIDE / long
        current = img
        current_w, current_h = w, h

        # 分步放大
        while True:
            cur_long = _long_side(current_w, current_h)
            if cur_long >= MIN_LONG_SIDE:
                break
            remaining = MIN_LONG_SIDE / cur_long
            step_scale = min(UPSCALE_STEP, remaining)
            new_w = max(int(current_w * step_scale), current_w + 1)
            new_h = max(int(current_h * step_scale), current_h + 1)
            current = current.resize((new_w, new_h), Image.LANCZOS)

            # 步间轻锐化（非最后一步）
            cur_long = _long_side(new_w, new_h)
            if cur_long < MIN_LONG_SIDE:
                current = sharpen(current, radius=STEP_SHARPEN_RADIUS, percent=60)
            current_w, current_h = new_w, new_h

        print(f"  (放大 {w}×{h} → {current_w}×{current_h})", end="")
        return current

    # --- 中等尺寸，不做缩放 ---
    return img


def convert_image(src: Path, dst_dir: Path) -> list[Path]:
    """将单张非 PDF 图片转为 JPG，支持多帧（如 TIFF/AVIF）。"""
    img = Image.open(src)
    output_files = []
    frame = 0
    while True:
        frame_img = img.convert("RGB")
        frame_img = resize_for_ipad(frame_img)
        frame_img = sharpen(frame_img)
        if frame == 0:
            name = src.stem + ".jpg"
        else:
            name = f"{src.stem}_{frame + 1}.jpg"
        out_path = dst_dir / name
        frame_img.save(out_path, "JPEG", quality=OUTPUT_QUALITY)
        output_files.append(out_path)
        frame += 1
        try:
            img.seek(frame)
        except EOFError:
            break
    return output_files


def convert_pdf(src: Path, dst_dir: Path) -> list[Path]:
    """将 PDF 每一页渲染为独立 JPG，动态算倍率后缩放至 iPad 尺寸。"""
    pdf = pdfium.PdfDocument(src)
    n_pages = len(pdf)
    output_files = []
    for i in range(n_pages):
        page = pdf[i]
        # 获取页面尺寸（points），计算需要的渲染倍率
        page_w, page_h = page.get_size()
        page_long = max(page_w, page_h)

        # 渲染倍率：最低 2x 保底，长边至少够 iPad 宽边
        render_scale = max(2.0, TARGET_W / page_long)
        bitmap = page.render(scale=render_scale)
        pil_img = bitmap.to_pil()
        pil_img = resize_for_ipad(pil_img)
        pil_img = sharpen(pil_img)

        if n_pages == 1:
            out_path = dst_dir / f"{src.stem}.jpg"
        else:
            out_path = dst_dir / f"{src.stem}_p{i + 1}.jpg"
        pil_img.save(out_path, "JPEG", quality=OUTPUT_QUALITY)
        output_files.append(out_path)
    pdf.close()
    return output_files


def main():
    folder = input("请粘贴文件夹路径：").strip().strip('"')
    base = Path(folder)
    if not base.is_dir():
        print(f"路径不存在或不是文件夹：{base}")
        return

    files = [f for f in base.iterdir() if f.is_file()]
    if not files:
        print("文件夹内没有文件。")
        return

    total_ok, total_skip, total_fail = 0, 0, 0

    for f in sorted(files):
        ext = f.suffix.lower()
        if ext == ".pdf" and HAS_PDF:
            print(f"[PDF ] {f.name}", end=" ")
            try:
                out = convert_pdf(f, base)
                print(f"→ {len(out)} 张 JPG")
                total_ok += len(out)
            except Exception as e:
                print(f"失败：{e}")
                total_fail += 1
        elif ext in IMG_EXTENSIONS:
            print(f"[IMG ] {f.name}", end=" ")
            try:
                out = convert_image(f, base)
                print(f"→ {len(out)} 张 JPG")
                total_ok += len(out)
            except Exception as e:
                print(f"失败：{e}")
                total_fail += 1
        elif ext in {".jpg", ".jpeg"}:
            total_skip += 1
        else:
            total_skip += 1

    print(f"\n完成：成功 {total_ok}，跳过 {total_skip}，失败 {total_fail}")


if __name__ == "__main__":
    main()
