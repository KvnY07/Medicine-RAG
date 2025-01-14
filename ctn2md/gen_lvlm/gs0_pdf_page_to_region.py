import os
import sys
import logging

# import re
from typing import List, Tuple, Optional  # , Dict

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

IMG_EXT = "jpg"  # or "png"
JPG_QUALITY = 90  # 95


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


def _merge_all_rects(page, rect_list):
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


def gs0_parse_non_text_rects_in_page(
    md_info: MdInfo, page: fitz.Page, page_index: int, pname_page_name: str
) -> List[Tuple[float, float, float, float]]:
    """
    Parse drawings in the page and merge adjacent rectangles.
    """

    # 提取画的内容
    drawings = page.get_drawings()

    # 忽略掉长度小于30的水平直线
    is_short_line = (
        lambda x: abs(x["rect"][3] - x["rect"][1]) < 1
        and abs(x["rect"][2] - x["rect"][0]) < 30
    )  # noqa
    drawings = [drawing for drawing in drawings if not is_short_line(drawing)]

    # 转换为shapely的矩形
    rect_list_drawing = [sg.box(*drawing["rect"]) for drawing in drawings]
    merged_rects_drawing = _merge_all_rects(page, rect_list_drawing)
    logging.info(
        f"page_index:{page_index} has number of rect_list_drawing: {len(rect_list_drawing)} after merge: {len(merged_rects_drawing)}"
    )

    # 提取图片区域
    images = page.get_image_info()
    rect_list_image = [sg.box(*image["bbox"]) for image in images]
    merged_rects_image = _merge_all_rects(page, rect_list_image)
    logging.info(
        f"page_index:{page_index} has number of rect_list_image: {len(rect_list_image)} after merge: {len(merged_rects_image)}"
    )

    merged_rects = merged_rects_drawing + merged_rects_image

    return [rect.bounds for rect in merged_rects]


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

    merged_rects_bounds = gs0_parse_non_text_rects_in_page(md_info, page, page_no)
    rich.print(merged_rects_bounds)
