import os
import sys

# import random
# import re
# import shutil
import json
import logging

import rich
from PIL import Image
from dotenv import load_dotenv

load_dotenv()

if "./" not in sys.path:
    sys.path.append("./")

from ctn2md.gen_lp.lp_base import (
    PAGE_IMG_STATUS,
    get_page_images,
    analyse_image_content,
)
from ctn2md.src.md_info_base import MIFN, MdInfo
from ctn2md.src.md_process_plc import (
    has_injected_plc_comment,
    inject_plc_comment_to_page,
    extract_plc_info_from_comment,
    separate_heading_and_plc_comment,
)
from ctn2md.utils.util_logging import setup_logger_handlers

# 常量定义
MIN_WIDTH = 198  # 图像最小宽度（像素）
MIN_HEIGHT = 198  # 图像最小高度（像素）
MIN_AREA = 128 * 128  # 图像最小面积（像素）

MIN_IMG_RELEVANCE_SCORE = 2.0  # 0 - 10


def _select_meanful_image_by_size(fname_image, md_info):
    """
    检查图像的合理性，并返回描述和新图像路径。
    :param image_file: 图像文件名
    :param md_info: 上下文信息字典
    :return: (简洁说明, 新的图像文件名) 或 (None, None) 表示不合适的图像
    """
    out_dir = md_info.get_out_dir()
    image_path = os.path.join(out_dir, fname_image)

    # 1. 图像是否存在
    if not os.path.exists(image_path):
        logging.warning(f"PIR: 无法读取图像 {image_path}")
        return None, "not exist"

    # 2. 检查图像尺寸
    try:
        with Image.open(image_path) as img:
            width, height = img.size
            if width < MIN_WIDTH or height < MIN_HEIGHT:
                logging.warning(
                    f"PIR: 图像高宽太小 {os.path.basename(image_path)} {width, height}"
                )
                return None, "too small"  # 图像太小
            if width * height < MIN_AREA:
                logging.warning(
                    f"PIR: 图像面积太小 {os.path.basename(image_path)} {width * height} < {MIN_AREA}"
                )
                return None, "too small"  # 图像太小
    except Exception as e:
        logging.warning(f"PIR: 无法读取图像 {image_path}，错误: {e}")
        return None, "access error"
    return True, None


def _find_closest_heading(
    image, headings, page, y_threshold_ratio=None, x_tolerance_ratio=None
):
    """
    根据页面的尺寸和图像的位置动态计算 y_threshold 和 x_tolerance，寻找视觉上最近的 heading。

    :param image: 图像数据，包含 'x', 'y' 等信息
    :param headings: 所有的 headings，包含 'type', 'lvl', 'value', 'bBox' 等信息
    :param page: 页面数据，包含 'width', 'height' 等信息，用来计算动态阈值
    :param y_threshold_ratio: Y 坐标的容忍比例，决定图像上下可接受的距离
    :param x_tolerance_ratio: X 坐标的容忍比例，决定图像和标题在水平方向上的接近程度
    :return: 最近的 heading 对象
    """
    # 获取页面的宽度和高度
    page_width = page["width"]
    page_height = page["height"]

    # 计算页面的宽高比
    page_ratio = page_width / page_height

    # 根据页面类型调整阈值
    if page_ratio > 1:  # PPT类型页面，宽大于高
        y_threshold_ratio = y_threshold_ratio or 0.3  # 放宽y方向的容忍度
        x_tolerance_ratio = x_tolerance_ratio or 0.4  # 放宽x方向的容忍度
    else:  # A4类型页面，宽小于高
        y_threshold_ratio = y_threshold_ratio or 0.3  # 严格要求y方向的阈值
        x_tolerance_ratio = x_tolerance_ratio or 0.4  # 适中的x容忍度

    # 计算动态的 y_threshold 和 x_tolerance
    y_threshold = page_height * y_threshold_ratio  # 垂直方向阈值
    x_tolerance = page_width * x_tolerance_ratio  # 水平方向容忍度

    # 设置阈值的最大限制，避免过大的容忍度
    y_threshold = min(y_threshold, page_height * 0.5)  # 最大不超过页面的50%
    x_tolerance = min(x_tolerance, page_width * 0.4)  # 最大不超过页面的25%
    logging.info(f"FCH: y_threshold: {y_threshold}")
    logging.info(f"FCH: x_tolerance: {x_tolerance}")

    closest_heading = None
    min_distance = float("inf")  # 初始化最小距离为无穷大

    # 获取图像的上下边界坐标（仅使用图像的y坐标和页面高度来估算）
    image_y_top = image["y"]
    image_x_left = image["x"]
    if (image_y_top < page_height * 0.1) and (image_x_left < page_width * 0.1):
        return None

    for heading in headings:
        # 跳过没有 bBox 的 heading
        if "bBox" not in heading:
            continue

        invalid = False
        for key in heading["bBox"].keys():
            if heading["bBox"][key] is None:
                invalid = True
        if invalid:
            continue

        # 计算y方向的距离
        heading_y_top = heading["bBox"]["y"]
        y_distance = abs(image_y_top - heading_y_top)

        # 计算x方向的距离
        heading_x_left = heading["bBox"]["x"]
        x_distance = abs(image_x_left - heading_x_left)

        # 调试日志：记录y和x的距离
        logging.debug(
            f"Image '{image['name']}' vs Heading '{heading['value']}': "
            f"y_distance={y_distance}, x_distance={x_distance}, "
            f"y_threshold={y_threshold}, x_tolerance={x_tolerance}"
        )

        # 如果y方向的距离小于阈值，检查x方向的容忍度
        if y_distance < y_threshold:
            if x_distance <= x_tolerance:
                total_distance = y_distance + x_distance  # 总距离：y 距离 + x 距离
                if total_distance < min_distance:
                    min_distance = total_distance
                    closest_heading = heading

    # 如果没有找到符合条件的heading，记录警告
    if closest_heading is None:
        logging.warning(
            f"No heading found for image '{image['name']}'. "
            f"y_threshold={y_threshold}, x_tolerance={x_tolerance}. "
            f"Try adjusting these thresholds."
        )

    return closest_heading


class Page2Markdown:
    def __init__(self, job_id, page, total_pages, md_info, pages_images):
        self.job_id = job_id
        self.page = page
        self.total_pages = total_pages
        self.md_info = md_info
        self.pages_images = pages_images

        self.page_no = page.get("page", None)
        self.page_width = page.get("width", None)
        self.page_height = page.get("height", None)

        self.md_page = page.get("md", None)
        self.items = page.get("items", None)

        self.ocr_all_text = " "
        self.ocr_all_confidence = 0
        self.ocr_text_ratio = 0

        self.images_selected_embd = []
        self.images_selected_page = []
        self.images_unselected = []

        if MIFN.LP_P2M_INFO not in md_info:
            md_info[MIFN.LP_P2M_INFO] = {}
        if self.page_no not in md_info[MIFN.LP_P2M_INFO]:
            md_info[MIFN.LP_P2M_INFO][self.page_no] = {}
        self.md_info_cur_page = md_info[MIFN.LP_P2M_INFO][self.page_no]

        self.md_page_plc_init = None
        self.md_page_plc_init_lines = None

        self.analysed = False
        self.analyse()

    def analyse(self):
        if self.analysed:
            return
        self.md_page_plc_init = inject_plc_comment_to_page(
            self.md_page, self.page_no, self.total_pages, self.md_info
        )

        self.analyse_ocr()
        self.analyse_images()
        self.analysed = True

    def analyse_ocr(self):
        self.ocr_all_text = " "
        tmc = 0
        images_at_cur_page = self.page.get("images", None)
        for image in images_at_cur_page:
            ocr = image.get("ocr", None)
            if ocr is None:
                continue
            for oi in ocr:
                confidence = oi.get("confidence", None)
                text = oi.get("text", None)
                if confidence and text:
                    tmc += len(text) * float(confidence)
                    self.ocr_all_text += text
        self.ocr_all_confidence = round(float(tmc / len(self.ocr_all_text)), 2)
        all_page_text = self.page.get("text").replace(" ", "")
        self.ocr_text_ratio = round(
            len(self.ocr_all_text) / (len(all_page_text) + 1), 2
        )

        logging.info(
            f"P2M: ocr_all_confidence: {self.ocr_all_confidence} for text_len:{len(self.ocr_all_text)} in a page with full_text_len:{len(all_page_text)} ocr_text_ratio:{self.ocr_text_ratio} "
        )
        logging.info(f"P2M: is_ocr_page: {self.is_ocr_page()}")
        if self.is_ocr_page() and (self.ocr_all_confidence < 0.6):
            logging.warning(
                f"P2M: is_ocr_page: {self.is_ocr_page()} with low ocr_all_confidence:{self.ocr_all_confidence}"
            )

        self.md_info_cur_page["ocr_all_confidence"] = self.ocr_all_confidence
        self.md_info_cur_page["ocr_text_ratio"] = self.ocr_text_ratio
        self.md_info_cur_page["ocr_len_orc"] = len(self.ocr_all_text)
        self.md_info_cur_page["ocr_len_full"] = len(all_page_text)

    def is_ocr_page(self):
        if self.ocr_text_ratio > 0.90:
            return True
        return False

    def analyse_images(self):
        self.images_selected_embd = []
        self.images_selected_page = []
        self.images_unselected = []

        self.analyse_images_filter_scan()
        self.analyse_images_embd_control()
        self.analyse_images_embd_auto()

        logging.info(f"P2M: images_selected_embd: {len(self.images_selected_embd)}")
        logging.info(f"P2M: images_selected_page: {len(self.images_selected_page)}")
        logging.info(f"P2M: images_unselected: {len(self.images_unselected)}")

        self.md_info_cur_page["images_selected_embd"] = self.images_selected_embd
        self.md_info_cur_page["images_selected_page"] = self.images_selected_page
        self.md_info_cur_page["images_unselected"] = self.images_unselected

    def analyse_images_filter_scan(self):
        # if the image is too small to query (no relance content to query)
        images = get_page_images(self.pages_images, self.page_no, self.total_pages)
        for image in images:
            name = image.get("name", None)
            full_name = name
            if not name.startswith(self.job_id):
                full_name = f"{self.job_id}-{name}"
            val, reason = _select_meanful_image_by_size(full_name, self.md_info)
            if val:
                image["name"] = full_name
                if name.find("img_p") != -1:
                    self.images_selected_embd.append(image)
                else:
                    self.images_selected_page.append(image)
            else:
                image["pi_status"] = f"{PAGE_IMG_STATUS.REMOVED}: {reason}"
                self.images_unselected.append(image)

    def _find_heading_for_plc_id(self, plc_id):
        if plc_id.find(":") != -1:
            plc_id = plc_id.split(":")[1]
        if self.md_page_plc_init_lines is None:
            if self.md_page_plc_init is None:
                raise ValueError("what happened?")
            self.md_page_plc_init_lines = self.md_page_plc_init.splitlines()

        for line in self.md_page_plc_init_lines:
            if not line.startswith("#"):
                continue
            if not has_injected_plc_comment(line):
                continue

            heading, plc_comment = separate_heading_and_plc_comment(
                line, with_plc_id=True
            )
            if len(plc_comment) == 0:
                continue

            plc_info = extract_plc_info_from_comment(plc_comment)
            if plc_info is None:
                continue

            if plc_info["PlcId"] == plc_id:
                return heading
        return None

    def analyse_images_embd_control(self):
        images = get_page_images(self.pages_images, self.page_no, self.total_pages)
        for image in images:
            if image.get("pi_status", None):
                continue

            plc_id = image.get("plc_id", None)
            if plc_id is None:
                continue

            if plc_id.startswith("*"):
                continue

            # find heading for the image as we know the plc_id
            heading = self._find_heading_for_plc_id(plc_id)
            if heading is None:
                continue

            image["closest_heading"] = {"md": heading.strip()}
            image["i2h"] = "mctl"

    def analyse_images_embd_auto(self):
        # find where to position the image if there is not position control
        found = 0
        headings = [item.copy() for item in self.items if item["type"] == "heading"]
        rich.print(headings)
        for image in self.images_selected_embd:
            if image.get("plc_id", None):
                continue
            rich.print(image)
            closest_heading = _find_closest_heading(image, headings, self.page)
            if closest_heading is not None:
                image["closest_heading"] = closest_heading
                closest_heading["md"] = closest_heading["md"].strip()
                image["i2h"] = "auto"
                found += 1
        logging.info(f"P2M: closet_heading founded: {found}")

    def save_page_markdown(self):
        # rich.print(self.page)

        mctl_lp_need_image_ref = self.md_info.get_md_control(
            "mctl_lp_need_image_ref", True
        )

        md_imgs_ref_at_end = ""
        if mctl_lp_need_image_ref:
            md_page_plc_with_embed_img_ref = self.inject_images_at_right_position(
                self.md_page_plc_init
            )
            md_imgs_ref_at_end = self.composite_all_not_positioned_ref_as_markdown()

        md_page_all = md_page_plc_with_embed_img_ref + md_imgs_ref_at_end
        fname_page = self.save_md_page(md_page_all)

        return fname_page

    def get_page_md_fname(self):
        return f"{self.job_id}-content_p{self.page_no}.md"

    def _need_gen_md_page(self, pname_page_md):
        if not os.path.isfile(pname_page_md):
            return True
        mctl_lp_notouch_pages = self.md_info.get_md_control_notouch(
            "mctl_lp_notouch_pages", []
        )
        if self.page_no in mctl_lp_notouch_pages:
            return False
        return True

    def save_md_page(self, md_page_all):
        try:
            out_dir = self.md_info.get_out_dir()
            fname_page_md = self.get_page_md_fname()
            pname_page_md = os.path.join(out_dir, fname_page_md)

            if self._need_gen_md_page(pname_page_md):
                with open(pname_page_md, "w", encoding="utf8") as f:
                    f.write(md_page_all)
            return fname_page_md
        except Exception as ex:
            logging.exception(ex)
        return None

    def get_img_ref_markdown(self, fname_image, closest_heading=None):
        dir_out = self.md_info.get_out_dir()
        pname_image = os.path.join(dir_out, fname_image)
        if not os.path.isfile(pname_image):
            return None, "not_exist"

        doc_title = self.md_info.get_doc_title()
        if closest_heading is not None:
            content_around = f"#document title: '{doc_title}'\n, ## content in current page: {self.page['md'][:400]}...\n ##around heading: {closest_heading['md']}:\n"
        else:
            content_around = f"#document title: '{doc_title}'\n, ## content in current page: {self.page['md'][:400]}:\n"

        relevance_score, figure_name, picture_discription = analyse_image_content(
            self.md_info, pname_image, content_around=content_around
        )
        if relevance_score is None:
            return None, "not_relevance"
        if relevance_score < self.md_info.get_md_control(
            "mctl_lp_min_img_relevance_score", MIN_IMG_RELEVANCE_SCORE
        ):
            return None, "low_relevance"

        picture_discription = picture_discription.replace('"', "'")

        basename = os.path.basename(pname_image)
        return f'![{figure_name}]({basename} "{picture_discription}")\n', None

    def composite_all_not_positioned_ref_as_markdown(self):
        img_refs = []
        for image in self.images_selected_embd:
            if image.get("pi_status", None):
                continue
            if image.get("plc_id", None):
                continue
            closest_heading = image.get("closest_heading", None)
            if closest_heading is None or closest_heading["md"].startswith("#"):
                fname = image.get("name", None)
                if fname is not None:
                    img_ref, reason = self.get_img_ref_markdown(fname)
                    if img_ref is not None:
                        img_refs.append(img_ref)
                        image["pi_status"] = PAGE_IMG_STATUS.POSITIONED
                    else:
                        image["pi_status"] = f"{PAGE_IMG_STATUS.REF_FILTERED}: {reason}"
        for image in self.images_selected_page:
            if image.get("pi_status", None):
                continue
            if image.get("plc_id", None):
                continue
            fname = image.get("name", None)
            if fname is not None:
                img_ref, reason = self.get_img_ref_markdown(fname)
                if img_ref is not None:
                    img_refs.append(img_ref)
                    image["pi_status"] = PAGE_IMG_STATUS.POSITIONED
                else:
                    image["pi_status"] = f"{PAGE_IMG_STATUS.REF_FILTERED}: {reason}"

        md_imgs = ""
        if len(img_refs) > 0:
            md_imgs = "\n\n" + "\n".join(img_refs) + "\n"
        return md_imgs

    def inject_images_at_right_position(self, md_page_plc):
        # 1. 按行切割 Markdown
        lines = md_page_plc.split("\n")

        # 2. 逐行加工处理
        processed_lines = []
        for line in lines:
            new_line = None
            if line.startswith("#"):
                for image in self.images_selected_embd:
                    if image.get("pi_status", None):
                        continue
                    closest_heading = image.get("closest_heading", None)
                    if closest_heading is not None:
                        if line.startswith(closest_heading["md"]):
                            fname = image.get("name", None)
                            if fname is not None:
                                closest_heading["md"] = "* " + closest_heading["md"]
                                img_ref, reason = self.get_img_ref_markdown(
                                    fname, closest_heading=closest_heading
                                )
                                if img_ref is not None:
                                    new_line = line + "\n" + img_ref + "\n"
                                    image[
                                        "pi_status"
                                    ] = f"{PAGE_IMG_STATUS.POSITIONED}: embeded"
                                else:
                                    image[
                                        "pi_status"
                                    ] = f"{PAGE_IMG_STATUS.REF_FILTERED}: {reason}@embed"
                                break
            if new_line is not None:
                line = new_line
            processed_lines.append(line)

        # 3. 将加工后的行重新合并为 Markdown 字符串
        processed_md = "\n".join(processed_lines)

        return processed_md


if __name__ == "__main__":
    setup_logger_handlers()

    # md_info_path = "_output/ctn2md_LongRAG/_info.json"
    # md_info_path = "_output/ctn2md_业绩案例_上汽内外饰DRE外包框架服务合同/_info.json"
    # md_info_path = "_output/ctn2md_业绩案例_上汽内外饰部CAD外包框架服务合同/_info.json"
    md_info_path = "_output/ctn2md_深度学习在视电阻率快速反演中的研究/_info.json"
    page_ndx = 3

    md_info = MdInfo(md_info_path)

    fname_json_result = md_info.get(MIFN.LP_FNAME_JSON_RESULT_NORMAL)

    with open(fname_json_result, "r", encoding="utf8") as f:
        json_result = json.load(f)

    json_result0 = json_result[0]
    job_id = md_info.get_unique_job_id()
    pages = json_result0["pages"]
    page = pages[page_ndx]
    total_pages = len(pages)

    p2m = Page2Markdown(job_id, page, total_pages, md_info)
    p2m.analyse()
    fname_page = p2m.save_page_markdown()
    md_info.save()

    rich.print(fname_page)
