import os
import re
import sys
import json
import shutil
import logging

import rich
import json_repair
from dotenv import load_dotenv

load_dotenv()

if "./" not in sys.path:
    sys.path.append("./")

from ctn2md.src.md_info_base import MIFN
from ctn2md.utils_vllm.vllm_description_qwen import generate_image_description_by_qwen

# from ctn2md.src.md_info_base import MIFN
# from ctn2md.utils.util_logging import setup_logger_handlers
from ctn2md.utils_llm.llm_gen_vllm_instruction_gpt import gen_vllm_instruction_by_gpt
from ctn2md.utils_llm.llm_gen_vllm_instruction_qwen import gen_vllm_instruction_by_qwen

g_question_num = 6000

IMG_DESP_EXT = "_desp.txt"


class PAGE_IMG_STATUS:
    REMOVED = "removed"
    POSITIONED = "positioned"
    IRRELEVANCE = "irrelevance"
    REF_FILTERED = "ref_filtered"


def _del_attr(image_copy, att_name):
    att = image_copy.get(att_name, None)
    if att is not None:
        del image_copy[att_name]


def prepare_pages_images(pages, md_info):
    pages_images = []
    job_id = md_info.get_unique_job_id()
    for page in pages:
        cur_page_images = page.get("images")
        if cur_page_images is not None:
            for image in cur_page_images:
                image_copy = image.copy()
                for name in [
                    "ocr",
                    "height",
                    "width",
                    "original_width",
                    "original_height",
                    "job_id",
                ]:
                    _del_attr(image_copy, name)
                name = image["name"]
                if job_id in name:
                    name = name.replace(job_id + "-", "")
                    image["name"] = name
                image_copy["page_no"] = page.get("page", None)
                pages_images.append(image_copy)

    mctl_lp_img_to_heading = md_info.get_md_control("mctl_lp_img_to_heading", None)
    if mctl_lp_img_to_heading is not None:
        for img_name, plc_id in mctl_lp_img_to_heading.items():
            for image in pages_images:
                image_name = image["name"]
                image_name = image_name.split(".")[0]
                if image_name.endswith(img_name):
                    image["plc_id"] = plc_id
    return pages_images


def get_page_images(pages_images, page_no, total_pages):
    images = []
    for image in pages_images:
        image_page_no = image["page_no"]
        if (image_page_no >= page_no - 1) and (image_page_no <= page_no + 1):
            if not image.get("pi_status", None):
                images.append(image)
    return images


def remove_misc_files_previous_round(md_info):
    """
    清理指定目录及其子目录下，以特定规则命名的文件：
    1. 以类似 UUID 前缀命名的文件。
    2. 以 xcs_前缀命名的 .md 文件。

    Args:
        md_info: 提供输出目录的对象，需实现 get_out_dir 方法。
    """
    # 获取输出目录
    out_dir = md_info.get_out_dir()
    aux_dir = md_info.get_aux_dir()
    os.makedirs(aux_dir, exist_ok=True)

    if not out_dir or not os.path.exists(out_dir):
        print(f"目录不存在或无效: {out_dir}")
        return

    # 正则模式
    uuid_pattern = re.compile(
        r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
    )
    xcs_pattern = re.compile(r"^xcs_.*\.md$")  # 匹配 xcs_ 开头的 .md 文件

    # 遍历目录及其子目录
    for root, _, files in os.walk(out_dir):
        files = sorted(files)
        for file_name in files:
            src_path = os.path.join(root, file_name)
            move = False
            if xcs_pattern.match(file_name):  # 匹配任意一个模式
                move = True
            elif uuid_pattern.match(file_name):
                move = True
                if file_name.endswith(IMG_DESP_EXT):
                    file_name = file_name.replace(IMG_DESP_EXT, "")
                if file_name in md_info[MIFN.FNAMES_IMGS]:
                    move = False
                elif file_name in md_info[MIFN.FNAMES_SNPS]:
                    move = False
            if move:
                try:
                    dst_path = os.path.join(aux_dir, os.path.basename(src_path))
                    shutil.move(src_path, dst_path)
                except Exception as e:
                    logging.exception(f"删除失败: {src_path}, 错误: {e}")


def _get_page_instruction(md_info, doc_title, content_around):
    global g_question_num
    mctl_lp_img_relevance_model = md_info.get_md_control(
        "mctl_lp_img_relevance_model", "qwen"
    )
    if mctl_lp_img_relevance_model == "qwen":
        instruction = gen_vllm_instruction_by_qwen(
            doc_title, content_around, question_num=g_question_num
        )
    else:
        instruction = gen_vllm_instruction_by_gpt(
            doc_title, content_around, question_num=g_question_num
        )
    g_question_num += 1
    return instruction


def _gen_figure_info(md_info, doc_title, content_around, image_path):
    instruction = _get_page_instruction(md_info, doc_title, content_around)
    resp = generate_image_description_by_qwen(image_path, instruction=instruction)
    if resp is None:
        raise ValueError("resp is None")
    resp_json = json_repair.repair_json(resp, return_objects=True, ensure_ascii=True)
    rich.print(resp_json)
    return resp_json


def _analyse_image_content_core(md_info, image_path, content_around=""):
    """
    模拟多模态处理函数，分析图像的内容是否有意义。

    :param md_page_file: 当前页的 MD 文件路径
    :param pathname_org_doc: 原始文档路径
    :param image_path: 图像的路径
    :return: (图像简洁说明, 新的图像路径) 或 (None, None) 如果图像无意义
    """
    # 1. 提取文档标题 (doc_title)
    # 从 pathname_org_doc 中去除目录和最后的扩展名
    doc_title = md_info.get_doc_title()

    # 3. 多模态分析逻辑
    try:
        resp_json = _gen_figure_info(md_info, doc_title, content_around, image_path)
        figure_name = resp_json.get("FigureName")
        relevance_score = resp_json.get("RelevanceScore")
        picture_discription = resp_json.get("PictureDescription")
        if relevance_score is not None:
            relevance_score = float(relevance_score)
        if figure_name is not None:
            if figure_name == "None":
                logging.warning(f"AIC: figure_name: {figure_name}")
    except Exception as e:
        logging.error(f"AIC: 处理多模态异常，错误: {e}")
        logging.exception(e)
        return None, None, None

    return relevance_score, figure_name, picture_discription


def analyse_image_content(md_info, image_path, content_around=""):
    pathname_img2desp = os.path.join(md_info.get_aux_dir(), "json_image_desp.json")
    json_cache = {}
    if os.path.isfile(pathname_img2desp):
        with open(pathname_img2desp, "r", encoding="utf-8") as f:
            try:
                json_cache = json.load(f)
            except Exception as ex:
                logging.exception(ex)

    doc_title = md_info.get_doc_title()
    key = f"{os.path.basename(image_path)}@{doc_title}>>>{content_around}"
    info = json_cache.get(key, None)
    if info is not None:
        return (
            info[0],
            info[1],
            info[2],
        )

    relevance_score, figure_name, picture_discription = _analyse_image_content_core(
        md_info, image_path, content_around=content_around
    )

    json_cache[key] = (relevance_score, figure_name, picture_discription)
    with open(pathname_img2desp, "w", encoding="utf-8") as f:
        json.dump(json_cache, f, indent=4, ensure_ascii=False)
    return relevance_score, figure_name, picture_discription
