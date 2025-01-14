PROMPT_INSTRUCT_IMG2REGION_QWEN = """
# 任务描述

你将接收一张输入图片，任务是基于视觉内容识别并定位所有的 **指定区域**，包括：
1. **全图区域 (Full Page)**：
   - 表示整幅图像的边界框。

2. **非典型文本区域 (Non-Typical Text Regions)**：
   - 可能没有，可以有一个，也可能有多个。包括：
     - **image**：插图、照片等纯图像区域，不包含文字。该区域应完全由图像内容构成。
     - **figure**：示意图、图示等非文本区域，通常没有文字或少量文字。
     - **chart**：柱状图、折线图、流程图等图表内容，图表区域仅包含数据和图形，不应包含文本描述。
---
## 输入说明

- 输入为一张图片。
- 请基于 **Qwen2-VL 的原生能力**，返回边界框和区域描述。
- **所有边界框 (`bbox`) 的坐标值均使用 Qwen2-VL 归一化数值**，范围在 `[0, 1000)` 内。
---
## 输出要求
请将你的输出格式化为标准的 **JSON 对象**，并包含以下字段：
### 1. 图像尺寸 (image_size)
   - `width`：图像的宽度（像素）。
   - `height`：图像的高度（像素）。
### 2. 区域列表 (regions)
   `regions` 字段为数组，表示图像中所有识别到的区域。每个区域对象应包含以下字段：
   - **`region_type`**：字符串，表示区域的类型，取值为：
      - `"full_page"`：表示整幅图像的区域。
      - `"image"`：表示插图、照片等视觉区域。
      - `"figure"`：表示示意图等视觉区域。
      - `"chart"`：表示图表，如柱状图、折线图等。
   - **`bbox`**：数组，表示归一化边界框坐标，格式为 `[x_top_left, y_top_left, x_bottom_right, y_bottom_right]`，所有值在 `[0, 1000)` 范围内。
---
## 输出格式示例
返回的 JSON 示例必须仅包含占位符，模型需尽力输出所有的区域信息（包括 0 个、1 个或多个 `image` 和 `chart` 区域）：
```json
{
  "image_size": {
    "width": "<image_width_in_pixels>",
    "height": "<image_height_in_pixels>",
  },
  "regions": [
    {
      "region_type": "full_page",
      "bbox": [0, 0, 1000, 1000],
      "description": "Entire page content"
    },
    {
      "region_type": "image",
      "bbox": [<x1_normalized>, <y1_normalized>, <x2_normalized>, <y2_normalized>],
      "description": "<Brief description of the image>"
    },
    {
      "region_type": "chart",
      "bbox": [<x1_normalized>, <y1_normalized>, <x2_normalized>, <y2_normalized>],
      "description": "<Brief description of the chart>"
    },
    ...
  ]
}

"""
