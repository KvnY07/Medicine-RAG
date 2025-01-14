import os
import sys
import logging

# import re
from typing import Dict, List, Tuple, Optional

import fitz  # PyMuPDF
import rich
import shapely.geometry as sg
from shapely.validation import explain_validity
from shapely.geometry.base import BaseGeometry

if "./" not in sys.path:
    sys.path.append("./")

from ctn2md.src.md_info_base import MIFN, MdInfo
from ctn2md.gen_lvlm.lvlm_base import get_job_id
from ctn2md.utils.util_logging import setup_logger_handlers

# from ctn2md.gen_lvlm.lvlm_image_cnt_type import get_image_cnt_type, LVLM_IMG_CNT_TYPE
from ctn2md.gen_lvlm.gs1_pdf_page_paint import detect_paint_regions
from ctn2md.gen_lvlm.gs1_pdf_page_table import detect_table_regions


def _is_near(rect1: BaseGeometry, rect2: BaseGeometry, distance: float = 20) -> bool:
    """
    Check if two rectangles are near each other if the distance between them is less than the target.
    """
    return rect1.buffer(0.1).distance(rect2.buffer(0.1)) < distance


def _is_horizontal_near(
    rect1: BaseGeometry, rect2: BaseGeometry, distance: float = 100
) -> bool:
    """
    Check if two rectangles are near horizontally if one of them is a horizontal line.
    """
    result = False
    if (
        abs(rect1.bounds[3] - rect1.bounds[1]) < 0.1
        or abs(rect2.bounds[3] - rect2.bounds[1]) < 0.1
    ):
        if (
            abs(rect1.bounds[0] - rect2.bounds[0]) < 0.1
            and abs(rect1.bounds[2] - rect2.bounds[2]) < 0.1
        ):
            result = abs(rect1.bounds[3] - rect2.bounds[3]) < distance
    return result


def _union_rects(rect1: BaseGeometry, rect2: BaseGeometry) -> BaseGeometry:
    """
    Union two rectangles.
    """
    return sg.box(*(rect1.union(rect2).bounds))


def _merge_rects(
    rect_list: List[BaseGeometry],
    distance: float = 20,
    horizontal_distance: Optional[float] = None,
) -> List[BaseGeometry]:
    """
    Merge rectangles in the list if the distance between them is less than the target.
    """
    merged = True
    while merged:
        merged = False
        new_rect_list = []
        while rect_list:
            rect = rect_list.pop(0)
            for other_rect in rect_list:
                if _is_near(rect, other_rect, distance) or (
                    horizontal_distance
                    and _is_horizontal_near(rect, other_rect, horizontal_distance)
                ):
                    rect = _union_rects(rect, other_rect)
                    rect_list.remove(other_rect)
                    merged = True
            new_rect_list.append(rect)
        rect_list = new_rect_list
    return rect_list


def _adsorb_rects_to_rects(
    source_rects: List[BaseGeometry],
    target_rects: List[BaseGeometry],
    distance: float = 10,
) -> Tuple[List[BaseGeometry], List[BaseGeometry]]:
    """
    Adsorb a set of rectangles to another set of rectangles.
    """
    new_source_rects = []
    for text_area_rect in source_rects:
        adsorbed = False
        for index, rect in enumerate(target_rects):
            if _is_near(text_area_rect, rect, distance):
                rect = _union_rects(text_area_rect, rect)
                target_rects[index] = rect
                adsorbed = True
                break
        if not adsorbed:
            new_source_rects.append(text_area_rect)
    return new_source_rects, target_rects


def _merge_rects_with_text_adjustments(page, rect_list):
    merged_rects = _merge_rects(rect_list, distance=10, horizontal_distance=100)
    merged_rects = [
        rect for rect in merged_rects if explain_validity(rect) == "Valid Geometry"
    ]

    # 将大文本区域和小文本区域分开处理: 大文本相小合并，小文本靠近合并
    is_large_content = lambda x: (len(x[4]) / max(1, len(x[4].split("\n")))) > 5  # noqa

    small_text_area_rects = [
        sg.box(*x[:4]) for x in page.get_text("blocks") if not is_large_content(x)
    ]
    large_text_area_rects = [
        sg.box(*x[:4]) for x in page.get_text("blocks") if is_large_content(x)
    ]

    _, merged_rects = _adsorb_rects_to_rects(
        large_text_area_rects, merged_rects, distance=0.1
    )  # 完全相交
    _, merged_rects = _adsorb_rects_to_rects(
        small_text_area_rects, merged_rects, distance=5
    )  # 靠近

    # 再次自身合并
    merged_rects = _merge_rects(merged_rects, distance=10)

    # 过滤比较小的矩形
    merged_rects = [
        rect
        for rect in merged_rects
        if rect.bounds[2] - rect.bounds[0] > 20 and rect.bounds[3] - rect.bounds[1] > 20
    ]
    return merged_rects


def _log_rect_area_stats(
    rects: List[sg.box], page_width: float, page_height: float, description: str
):
    total_area = sum(rect.area for rect in rects)
    page_area = page_width * page_height
    logging.info(
        f"{description}: Total Area={total_area:.2f}, Coverage={total_area / page_area:.2%}, "
        f"Count={len(rects)}"
    )


def _merge_adjacent_or_overlapping_non_text_rects(
    rect_list: List[sg.box], page_width: float, page_height: float, md_info: MdInfo
) -> List[sg.box]:
    """
    合并相邻或重叠的非文本矩形区域，根据包含和重叠规则进行合并。

    参数:
        rect_list (List[sg.box]): 输入的矩形列表。
        page_width (float): 页面宽度。
        page_height (float): 页面高度。
        md_info (MdInfo): 元数据信息对象，用于获取控制参数。

    返回:
        List[sg.box]: 合并后的矩形列表。
    """
    # merge_distance_ratio = md_info.get_md_control("mctrl_lvlm_merge_distance_ratio", 0.02)
    # merge_distance = min(page_width, page_height) * merge_distance_ratio

    def should_merge(rect1, rect2):
        """判断两个矩形是否需要合并."""
        # 规则 1：完全包含
        if rect1.contains(rect2):
            return True
        if rect2.contains(rect1):
            return True

        # 规则 2：重叠面积超过总面积的 20%
        intersection = rect1.intersection(rect2)
        if intersection.is_empty:
            return False

        intersection_area = intersection.area
        combined_area = rect1.area + rect2.area - intersection_area
        if intersection_area / combined_area > 0.2:
            return True

        return False

    # 合并矩形逻辑
    merged = True
    while merged:
        merged = False
        new_rect_list = []

        while rect_list:
            current = rect_list.pop(0)
            to_merge = []

            for other_rect in rect_list:
                if should_merge(current, other_rect):
                    to_merge.append(other_rect)

            # 合并当前矩形和需要合并的矩形
            for rect in to_merge:
                rect_list.remove(rect)
                current = sg.box(*current.union(rect).bounds)
                merged = True  # 如果找到需要合并的矩形，标记继续

            new_rect_list.append(current)

        rect_list = new_rect_list  # 更新矩形列表，继续下一轮合并

    return rect_list


def _get_rect_bounds(list_rects):
    return [rect.bounds for rect in list_rects]


"""
返回是 bounds list, 每一个 bounds 如下：
(x_min, y_min, x_max, y_max)
#### **参数说明**
1. **`x_min`**:
- 矩形左边界的 x 坐标。
- 表示该矩形区域在页面上的最左端位置。
2. **`y_min`**:
- 矩形下边界的 y 坐标。
- 表示该矩形区域在页面上的最下端位置。
3. **`x_max`**:
- 矩形右边界的 x 坐标。
- 表示该矩形区域在页面上的最右端位置。
4. **`y_max`**:
- 矩形上边界的 y 坐标。
- 表示该矩形区域在页面上的最上端位置。

#### **坐标系统**
- **绝对坐标**：
- 坐标基于 PDF 页面尺寸的绝对单位，通常是以点（point）为单位（1 点 = 1/72 英寸）。
- `(0, 0)` 通常是 PDF 页面左下角的起始点。
- `x` 值从左到右增加，`y` 值从下到上增加。
"""


def _gs1_parse_non_text_rects_in_page_core(
    md_info: MdInfo, page: fitz.Page, page_index: int
) -> Tuple[
    List[Tuple[float, float, float, float]],
    Dict[str, List[Tuple[float, float, float, float]]],
]:
    """
    解析 PDF 页面中的非文本区域，包括图片、绘制区域和表格。

    参数:
        md_info (MdInfo): 元数据信息对象，用于获取控制参数。
        page (fitz.Page): PDF 页面对象。
        page_index (int): 当前页面索引。

    返回:
        Tuple[List[Tuple[float, float, float, float]], Dict[str, List[Tuple[float, float, float, float]]]]:
            合并后的非文本区域矩形边界，以及原始分类区域的矩形边界字典。
    """
    # 提取图片区域
    images = page.get_image_info()
    rect_list_image = [sg.box(*image["bbox"]) for image in images]
    logging.info(
        f"page_index:{page_index} has number of rect_list_image: {len(rect_list_image)}"
    )

    # 猜测绘制区域
    rect_list_paint = detect_paint_regions(md_info, page)
    logging.info(
        f"page_index:{page_index} has number of rect_list_paint: {len(rect_list_paint)}"
    )

    # 猜测表格区域
    rect_list_table = detect_table_regions(md_info, page)
    # TODO: ethan_table ignore table for now
    rect_list_table = []
    logging.info(
        f"page_index:{page_index} has number of rect_list_table: {len(rect_list_table)}"
    )

    # 合并所有非文本区域
    merged_rects = rect_list_image + rect_list_paint + rect_list_table

    # 进行最终的合并和过滤
    page_width, page_height = page.mediabox_size
    final_merged_rects = _merge_adjacent_or_overlapping_non_text_rects(
        merged_rects, page_width, page_height, md_info
    )

    # 获取矩形边界列表
    merged_rects_bounds = _get_rect_bounds(final_merged_rects)

    # 分类别返回原始分类区域的矩形边界
    rects_list = {
        "rect_list_image": _get_rect_bounds(rect_list_image),
        "rect_list_paint": _get_rect_bounds(rect_list_paint),
        "rect_list_table": _get_rect_bounds(rect_list_table),
    }

    logging.info(
        f"page_index:{page_index} merged_rects_bounds: {len(merged_rects_bounds)}"
    )

    return merged_rects_bounds, rects_list


def gs1_parse_non_text_rects_in_page(
    md_info: MdInfo, page: fitz.Page, page_index: int, pname_page_name: str
) -> Tuple[
    List[Tuple[float, float, float, float]],
    Dict[str, List[Tuple[float, float, float, float]]],
]:
    merged_rects_bounds, _ = _gs1_parse_non_text_rects_in_page_core(
        md_info, page, page_index
    )
    return merged_rects_bounds


if __name__ == "__main__":

    setup_logger_handlers()

    # doc_pathname = "datasrc/exam/raw_docs/attention_is_all_you_need.pdf"
    doc_pathname = "datasrc/exam/raw_docs/LongRAG.pdf"
    page_no = 8

    output_dir = MdInfo.get_suggested_out_dir(doc_pathname, suffix="lvlm")

    job_id = get_job_id(doc_pathname)

    os.makedirs(output_dir, exist_ok=True)

    md_info = MdInfo(output_dir)
    md_info.set_doc_pathname(doc_pathname)
    md_info[MIFN.LVLM_CUR_JOB_ID] = job_id

    pdf_document = fitz.open(doc_pathname)
    page = pdf_document[page_no - 1]  # 0-based index

    merged_rects_bounds, rects_list = _gs1_parse_non_text_rects_in_page_core(
        md_info, page, page_no
    )
    rich.print(merged_rects_bounds)
    rich.print(rects_list)
