import sys
import logging
from typing import List  # , Tuple, Optional  # , Dict

import fitz  # PyMuPDF
import shapely.geometry as sg
from shapely.geometry import box as sg_box
from shapely.geometry.base import BaseGeometry

# import rich


if "./" not in sys.path:
    sys.path.append("./")

from ctn2md.src.md_info_base import MdInfo


def _add_rect_with_checks(
    rect: sg.box, rects: List[sg.box], page: fitz.Page, md_info: MdInfo
) -> None:
    """
    添加矩形时立即检测异常，并过滤掉过大的矩形。

    参数:
        rect (sg.box): 待添加的矩形。
        rects (List[sg.box]): 当前矩形列表。
        page (fitz.Page): PDF 页面对象，用于面积计算。
        md_info (MdInfo): 元数据信息对象。
    """
    page_width, page_height = page.mediabox_size
    page_area = page_width * page_height
    area_ratio_threshold = md_info.get_md_control("mctl_lvlm_paint_max_area_ratio", 0.5)

    rect_area = (rect.bounds[2] - rect.bounds[0]) * (rect.bounds[3] - rect.bounds[1])

    # 如果矩形过大（面积接近页面大小），则过滤
    if rect_area / page_area > area_ratio_threshold:
        logging.warning(
            f"Filtered large rect during addition: ({rect.bounds[0]:.2f}, {rect.bounds[1]:.2f}, {rect.bounds[2]:.2f}, {rect.bounds[3]:.2f})"
        )
        return

    rects.append(rect)


def _filter_large_rects(
    rects: List[BaseGeometry], page: fitz.Page, md_info: MdInfo
) -> List[BaseGeometry]:
    """
    剔除面积过大的矩形。

    参数:
        rects (List[BaseGeometry]): 输入的矩形列表。
        page (fitz.Page): PDF 页面对象。
        md_info (MdInfo): 元数据信息对象。

    返回:
        List[BaseGeometry]: 过滤后的矩形列表。
    """
    max_area_ratio = md_info.get_md_control("mctl_lvlm_paint_max_area_ratio", 0.7)
    page_width, page_height = page.mediabox_size
    page_area = page_width * page_height

    filtered_rects = []
    for rect in rects:
        rect_area = rect.area
        if rect_area > page_area * max_area_ratio:
            logging.debug(
                f"Removed Rect (Too Large): Area={rect_area:.2f}, "
                f"Bounds=({rect.bounds[0]:.2f}, {rect.bounds[1]:.2f}, "
                f"{rect.bounds[2]:.2f}, {rect.bounds[3]:.2f})"
            )
            continue
        filtered_rects.append(rect)

    return filtered_rects


def _filter_touching_content_area(
    rects: List[BaseGeometry], page: fitz.Page, md_info: MdInfo
) -> List[BaseGeometry]:
    """
    剔除触及内容区域外的矩形。

    参数:
        rects (List[BaseGeometry]): 输入的矩形列表。
        page (fitz.Page): PDF 页面对象。
        md_info (MdInfo): 元数据信息对象。

    返回:
        List[BaseGeometry]: 过滤后的矩形列表。
    """
    content_area_ratios = md_info.get_md_control(
        "mctl_lvlm_paint_page_content_area_ratios", (0.15, 0.15, 0.1, 0.1)
    )
    max_outside_ratio = md_info.get_md_control("mctl_lvlm_paint_max_outside_ratio", 0.1)
    buffer_ratio = md_info.get_md_control(
        "mctl_lvlm_paint_content_area_buffer_ratio", 0.05
    )

    page_width, page_height = page.mediabox_size
    content_x_min = page_width * content_area_ratios[0]
    content_x_max = page_width * (1 - content_area_ratios[1])
    content_y_min = page_height * content_area_ratios[2]
    content_y_max = page_height * (1 - content_area_ratios[3])

    buffer_x_min = content_x_min - page_width * buffer_ratio
    buffer_x_max = content_x_max + page_width * buffer_ratio
    buffer_y_min = content_y_min - page_height * buffer_ratio
    buffer_y_max = content_y_max + page_height * buffer_ratio

    content_area = sg_box(content_x_min, content_y_min, content_x_max, content_y_max)
    buffered_area = sg_box(buffer_x_min, buffer_y_min, buffer_x_max, buffer_y_max)

    filtered_rects = []

    for rect in rects:
        if not buffered_area.contains(rect):
            logging.debug(
                f"Removed Rect (Touches Outside Buffer): Bounds=({rect.bounds[0]:.2f}, {rect.bounds[1]:.2f}, "
                f"{rect.bounds[2]:.2f}, {rect.bounds[3]:.2f})"
            )
            continue

        intersection_area = rect.intersection(content_area).area
        outside_ratio = (
            (rect.area - intersection_area) / rect.area if rect.area > 0 else 0
        )
        if outside_ratio > max_outside_ratio:
            logging.debug(
                f"Removed Rect (Exceeds Outside Ratio {max_outside_ratio:.2%}): Outside={outside_ratio:.2%}, "
                f"Bounds=({rect.bounds[0]:.2f}, {rect.bounds[1]:.2f}, {rect.bounds[2]:.2f}, {rect.bounds[3]:.2f})"
            )
            continue

        filtered_rects.append(rect)

    return filtered_rects


def _filter_by_content_area_coverage(
    rects: List[BaseGeometry], page: fitz.Page, md_info: MdInfo
) -> List[BaseGeometry]:
    """
    根据内容区域的覆盖比例过滤矩形。

    参数:
        rects (List[BaseGeometry]): 输入的矩形列表。
        page (fitz.Page): PDF 页面对象。
        md_info (MdInfo): 元数据信息对象。

    返回:
        List[BaseGeometry]: 过滤后的矩形列表。
    """
    content_area_ratios = md_info.get_md_control(
        "mctl_lvlm_paint_page_content_area_ratios", (0.15, 0.15, 0.1, 0.1)
    )
    min_coverage_ratio = md_info.get_md_control(
        "mctl_lvlm_paint_min_coverage_ratio", 0.7
    )
    max_outside_ratio = md_info.get_md_control("mctl_lvlm_paint_max_outside_ratio", 0.1)

    page_width, page_height = page.mediabox_size
    content_x_min = page_width * content_area_ratios[0]
    content_x_max = page_width * (1 - content_area_ratios[1])
    content_y_min = page_height * content_area_ratios[2]
    content_y_max = page_height * (1 - content_area_ratios[3])

    content_area = sg_box(content_x_min, content_y_min, content_x_max, content_y_max)

    filtered_rects = []

    for rect in rects:
        intersection_area = rect.intersection(content_area).area
        rect_area = rect.area

        coverage_ratio = intersection_area / rect_area if rect_area > 0 else 0
        outside_ratio = (
            (rect_area - intersection_area) / rect_area if rect_area > 0 else 0
        )

        if coverage_ratio < min_coverage_ratio or outside_ratio > max_outside_ratio:
            logging.debug(
                f"Removed Rect (Coverage Check): Coverage={coverage_ratio:.2%}, Outside={outside_ratio:.2%}, "
                f"Bounds=({rect.bounds[0]:.2f}, {rect.bounds[1]:.2f}, {rect.bounds[2]:.2f}, {rect.bounds[3]:.2f})"
            )
            continue

        filtered_rects.append(rect)

    return filtered_rects


def _filter_rects(
    rects: List[BaseGeometry], page: fitz.Page, md_info: MdInfo
) -> List[BaseGeometry]:
    """
    对矩形列表进行多层过滤。

    参数:
        rects (List[BaseGeometry]): 输入的矩形列表。
        page (fitz.Page): PDF 页面对象。
        md_info (MdInfo): 元数据信息对象。

    返回:
        List[BaseGeometry]: 过滤后的矩形列表。
    """
    filtered_rects = rects

    # 剔除面积过大的矩形
    filtered_rects = _filter_large_rects(filtered_rects, page, md_info)

    # 剔除触及内容区域外的矩形
    filtered_rects = _filter_touching_content_area(filtered_rects, page, md_info)

    # 根据内容区域的覆盖比例过滤
    filtered_rects = _filter_by_content_area_coverage(filtered_rects, page, md_info)

    return filtered_rects


def _expand_and_absorb_regions_with_ratios(
    regions: List[sg.box], page: fitz.Page, md_info: MdInfo
) -> List[sg.box]:
    """
    扩展给定的区域并吸附页面中的文字块。

    参数:
        regions (List[sg.box]): 初始的区域列表。
        page (fitz.Page): PDF 的页面对象。
        md_info (MdInfo): 元数据信息对象，用于获取控制参数。

    返回:
        List[sg.box]: 扩展并吸附后的区域列表。
    """
    # 获取页面宽度和高度
    page_width, page_height = page.mediabox_size

    # 从 md_info 获取扩展控制参数（左、右、上、下的比例）
    paint_distance_ratios = md_info.get_md_control(
        "mctl_lvlm_paint_text_distance_ratio",
        (0.015, 0.015, 0.015, 0.028),  # 默认左、右、上、下的扩展比例
    )
    (
        text_x_left_distance_ratio,
        text_x_right_distance_ratio,
        text_y_up_distance_ratio,
        text_y_down_distance_ratio,
    ) = paint_distance_ratios

    text_blocks = [sg.box(*block[:4]) for block in page.get_text("blocks")]

    expanded_regions = []

    for region in regions:
        # 扩展当前区域
        expanded_region = sg.box(
            region.bounds[0] - page_width * text_x_left_distance_ratio,  # 左侧扩展
            region.bounds[1] - page_height * text_y_up_distance_ratio,  # 上方扩展
            region.bounds[2] + page_width * text_x_right_distance_ratio,  # 右侧扩展
            region.bounds[3] + page_height * text_y_down_distance_ratio,  # 下方扩展
        )

        # 吸附文字块
        for text_block in text_blocks:
            if expanded_region.intersects(text_block):
                region = sg.box(*region.union(text_block).bounds)

        expanded_regions.append(region)

    return expanded_regions


def _log_detected_regions(
    regions: List[sg.box], description: str, page: fitz.Page, md_info: MdInfo
) -> None:
    """
    记录检测到的矩形区域及其边界，仅记录面积最大的前 3 个合并区域。

    参数:
        regions (List[sg.box]): 要输出的矩形区域列表。
        description (str): 本次日志的描述信息。
        page (fitz.Page): PDF 的页面对象，用于计算区域面积占页面的比例。
        md_info (MdInfo): 元数据信息对象，用于控制参数。
    """
    if logging.getLogger().isEnabledFor(logging.DEBUG):
        regions = regions.copy()
        page_width, page_height = page.mediabox_size
        page_area = page_width * page_height

        merged_regions = _merge_adjacent_or_overlapping_rects(
            regions, page_width, page_height, md_info
        )
        logging.debug(f"{description}: {len(merged_regions)} merged regions detected.")

        sorted_regions = sorted(
            merged_regions,
            key=lambda region: (region.bounds[2] - region.bounds[0])
            * (region.bounds[3] - region.bounds[1]),
            reverse=True,
        )[:3]

        for idx, region in enumerate(sorted_regions):
            area = (region.bounds[2] - region.bounds[0]) * (
                region.bounds[3] - region.bounds[1]
            )
            area_ratio = area / page_area
            logging.debug(
                f"  Top {idx + 1} Merged Region: Area={area:.2f} ({area_ratio:.2%} of page), "
                f"Bounds=({region.bounds[0]:.2f}, {region.bounds[1]:.2f}, "
                f"{region.bounds[2]:.2f}, {region.bounds[3]:.2f})"
            )


def _merge_adjacent_or_overlapping_rects(
    rect_list: List[sg.box], page_width: float, page_height: float, md_info: MdInfo
) -> List[sg.box]:
    """
    合并相邻或重叠的矩形区域，并引入页面相关的距离限制和最大合并限制。

    参数:
        rect_list (List[sg.box]): 输入的矩形列表。
        page_width (float): 页面宽度。
        page_height (float): 页面高度。
        md_info (MdInfo): 元数据信息对象，用于获取合并距离的控制参数。

    返回:
        List[sg.box]: 合并后的矩形列表。
    """
    # 从 md_info 获取合并距离比例
    distance_ratio = md_info.get_md_control(
        "mctl_lvlm_paint_merge_distance_ratio", 0.02
    )
    merge_distance = min(page_width, page_height) * distance_ratio
    page_area = page_width * page_height

    logging.debug(f"Merge distance set to: {merge_distance:.2f}")
    merged = True
    while merged:
        merged = False
        new_rect_list = []

        while rect_list:
            rect = rect_list.pop(0)
            to_merge = []

            for other_rect in rect_list:
                # 判断是否需要合并
                if rect.distance(other_rect) < merge_distance or rect.intersects(
                    other_rect
                ):
                    to_merge.append(other_rect)

            # 合并当前矩形和所有需要合并的矩形
            for merge_rect in to_merge:
                rect_list.remove(merge_rect)
                rect = sg.box(*(rect.union(merge_rect).bounds))  # 合并为一个新矩形

                # 检查合并后的矩形是否过大
                if (rect.bounds[2] - rect.bounds[0]) * (
                    rect.bounds[3] - rect.bounds[1]
                ) > page_area * 0.8:
                    logging.debug(f"Skipping overly large merged rect: {rect.bounds}")
                    continue

                merged = True  # 如果找到需要合并的矩形，标记继续

            new_rect_list.append(rect)

        rect_list = new_rect_list  # 更新矩形列表，继续下一轮合并

    return rect_list


def _add_and_log_rects(
    new_rects: List[sg.box],
    detected_rects: List[sg.box],
    page: fitz.Page,
    md_info: MdInfo,
    description: str,
) -> None:
    """
    添加新检测的矩形并记录日志，包括新增矩形和合并后的区域变化。

    参数:
        new_rects (List[sg.box]): 新检测到的矩形列表。
        detected_rects (List[sg.box]): 当前存储的检测矩形列表。
        page (fitz.Page): PDF 页面对象，用于获取页面信息。
        md_info (MdInfo): 元数据信息对象，用于获取控制参数。
        description (str): 本次添加操作的描述。
    """
    # 添加新矩形到检测列表
    for rect in new_rects:
        _add_rect_with_checks(rect, detected_rects, page, md_info)

    # 日志记录新检测到的矩形
    _log_detected_regions(new_rects, f"Newly detected {description}", page, md_info)

    # 检查合并后的整体区域变化
    _log_detected_regions(
        detected_rects, f"Detected rectangles after adding {description}", page, md_info
    )


def detect_paint_regions(
    md_info: MdInfo,
    page: fitz.Page,
) -> List[sg.box]:
    """
    检测 PDF 页面中可能是绘制图片的区域。

    参数:
        md_info (MdInfo): 元数据信息对象，用于获取控制参数。
        page (fitz.Page): PDF 的单页对象。

    返回:
        List[sg.box]: 检测到的绘制图片的矩形区域列表（Shapely 矩形）。
    """
    logging.debug(f"Processing page: {page.number}")

    page_width, page_height = page.mediabox_size
    drawings = page.get_drawings()
    logging.debug(f"Total drawings extracted: {len(drawings)}")

    detected_rects = []

    # 方法 1: 填充颜色的矩形
    filled_rects = [
        sg.box(*drawing["rect"])
        for drawing in drawings
        if drawing.get("fill") is not None
    ]
    _add_and_log_rects(filled_rects, detected_rects, page, md_info, "filled rectangles")

    # 方法 2: 边框形状检测
    bordered_rects = [
        sg.box(*drawing["rect"])
        for drawing in drawings
        if drawing.get("stroke") is not None
    ]
    _add_and_log_rects(
        bordered_rects, detected_rects, page, md_info, "bordered rectangles"
    )

    # 方法 3: 路径复杂度检测
    complex_paths = [
        sg.box(*drawing["rect"])
        for drawing in drawings
        if len(drawing.get("points", [])) > 10
    ]
    _add_and_log_rects(complex_paths, detected_rects, page, md_info, "complex paths")

    # 方法 4: 嵌套矩形检测
    nested_rects = []
    for outer in drawings:
        outer_box = sg.box(*outer["rect"])
        for inner in drawings:
            inner_box = sg.box(*inner["rect"])
            if outer_box.contains(inner_box) and outer_box != inner_box:
                nested_rects.append(outer_box)
    _add_and_log_rects(nested_rects, detected_rects, page, md_info, "nested rectangles")

    # 方法 5: 柱状图特征检测
    bar_chart_rects = []
    for rect in detected_rects:
        widths = [r.bounds[2] - r.bounds[0] for r in detected_rects]
        if len(set(widths)) == 1 and len(detected_rects) > 5:
            bar_chart_rects.extend(detected_rects)
    _add_and_log_rects(
        bar_chart_rects, detected_rects, page, md_info, "bar chart rectangles"
    )

    # 方法 6: 高密度区域检测
    dense_regions = []
    for rect in detected_rects:
        density = sum(
            1 for drawing in drawings if sg.box(*drawing["rect"]).intersects(rect)
        )
        if density > md_info.get_md_control("mctl_lvlm_dense_region_threshold", 15):
            dense_regions.append(rect)
    _add_and_log_rects(dense_regions, detected_rects, page, md_info, "dense regions")

    # 过滤、合并和扩展检测区域
    filtered_rects = _filter_rects(detected_rects, page, md_info)
    merged_rects = _merge_adjacent_or_overlapping_rects(
        filtered_rects, page_width, page_height, md_info
    )
    expanded_paint_regions = _expand_and_absorb_regions_with_ratios(
        merged_rects, page, md_info
    )

    logging.info(
        f"Final number of expanded paint regions: {len(expanded_paint_regions)}"
    )
    return expanded_paint_regions
