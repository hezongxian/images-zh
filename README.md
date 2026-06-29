# 批量图片转 JPG（iPad 适配版）

将文件夹内的 PDF、WebP、PNG、TIFF、AVIF、HEIC 等格式批量转换为 JPG，自动适配 iPad Pro 12.9 英寸分辨率（2732×2048）。

## 功能

- **多格式支持**：PDF（每页一张图）、WebP、PNG、BMP、TIFF（含多帧）、AVIF、HEIC/HEIF 等
- **iPad 屏幕适配**：大图等比缩小不丢清晰度，小图分步放大并用 Unsharp Mask 锐化
- **PDF 动态渲染**：根据页面尺寸自动计算渲染倍率，保证清晰度
- **自动锐化**：所有输出图片统一过 Unsharp Mask，文字和边缘更锐利
- **已存在的 JPG 自动跳过**，不做重复处理

## 环境要求

- Python 3.8+
- Pillow
- pypdfium2（PDF 转换必需）

## 安装

```bash
pip install pillow pypdfium2
```

## 使用

```bash
python convert_to_jpg.py
```

粘贴目标文件夹路径，回车。脚本会扫描文件夹内所有文件，自动转换并输出到同一目录。

### 运行示例

```
请粘贴文件夹路径：D:\Downloads\images
[PDF ] report.pdf   (缩小 3854×2860 → 2732×2028) → 3 张 JPG
[IMG ] photo.webp   (放大 800×600 → 2200×1650) → 1 张 JPG
[IMG ] scan.png → 1 张 JPG

完成：成功 4，跳过 2，失败 0
```

## 配置

脚本顶部的常量均可修改：

| 参数 | 默认值 | 说明 |
|---|---|---|
| `OUTPUT_QUALITY` | `95` | JPG 质量，1-100 |
| `TARGET_W` | `2732` | iPad 横向像素 |
| `TARGET_H` | `2048` | iPad 纵向像素 |
| `MIN_LONG_SIDE` | `2200` | 小图触发放大的长边阈值 |
| `UPSCALE_STEP` | `1.5` | 分步放大倍率上限 |
| `STEP_SHARPEN_RADIUS` | `0.6` | 步间轻锐化半径 |
| `SHARPEN_ENABLED` | `True` | 锐化开关 |
| `SHARPEN_RADIUS` | `1.2` | 最终锐化半径 |
| `SHARPEN_PERCENT` | `100` | 最终锐化强度 |
| `SHARPEN_THRESHOLD` | `2` | 锐化噪声阈值 |
| `DELETE_ORIGINAL` | `False` | 设为 `True` 删除原文件 |

## iPad 尺寸处理逻辑

| 图片尺寸 | 处理方式 |
|---|---|
| 任一维度超出 2732×2048 | 等比缩小至框内，LANCZOS 采样 |
| 长边低于 2200px | 分步放大至长边达标，步间轻锐化 |
| 长边 2200~2732 且未超标 | 不缩放，仅最终锐化 |

## 支持格式

| 格式 | 扩展名 | 备注 |
|---|---|---|
| PDF | `.pdf` | 需要 pypdfium2 |
| WebP | `.webp` | |
| PNG | `.png` | |
| BMP | `.bmp` | |
| TIFF | `.tiff`, `.tif` | 支持多帧 |
| AVIF | `.avif` | |
| HEIC | `.heic`, `.heif` | iPhone 照片 |
| JPEG | `.jpeg`, `.jfif` | |

`.jpg` 文件和不在列表中的扩展名会被跳过。
