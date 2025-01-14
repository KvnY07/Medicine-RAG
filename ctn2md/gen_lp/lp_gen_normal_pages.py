import os
import sys

# import random
# import re
import json
import logging

import rich
from dotenv import load_dotenv

# import shutil

load_dotenv()

if "./" not in sys.path:
    sys.path.append("./")

from ctn2md.gen_lp.lp_base import prepare_pages_images, remove_misc_files_previous_round
from ctn2md.src.md_info_base import MIFN, MdInfo
from ctn2md.utils.util_logging import setup_logger_handlers
from ctn2md.gen_lp.lp_unique_job import n2u_replace_fnames, n2u_update_md_content
from ctn2md.gen_lp.lp_page2markdown import Page2Markdown


def _get_llamaparse_normal(md_info):
    from llama_parse import LlamaParse
    from llama_parse.utils import Language

    language = md_info.get_md_control("mctl_lp_langauge", Language.SIMPLIFIED_CHINESE)
    # TODO: ethan_take_screenshot can be realiy replace by pyMuPDF which has much faster dumping performance
    take_screenshot = md_info.get_md_control("mctl_lp_take_screenshot", False)
    disable_ocr = md_info.get_md_control("mctl_lp_disable_ocr", False)

    LLAMAPARSE_API_KEY = os.environ.get("LLAMAPARSE_API_KEY")
    parser = LlamaParse(
        api_key=LLAMAPARSE_API_KEY,  # 替换为您的 API 密钥
        result_type="markdown",  # 选择 "markdown" 格式输出
        verbose=True,
        language=language,  # "ch_sim",
        # page_suffix="mark_page_separator_{page_number}"
        invalidate_cache=True,
        check_interval=3,
        max_timeout=30 * 60,
        take_screenshot=take_screenshot,
        disable_ocr=disable_ocr,
    )
    return parser


def _dump_normal_md_page_from_lp_json_result(json_result, md_info):
    out_dir = md_info.get_out_dir()
    os.makedirs(out_dir, exist_ok=True)

    job_ids_set = set()
    file_paths_set = set()
    job_metadata = {}
    fnames_pages = []
    for node in json_result:
        job_id = node.get("job_id", None)
        job_ids_set.add(job_id)
        file_path = node.get("file_path", None)
        file_paths_set.add(file_path)
        job_metadata = node.get("job_metadata", {})

        logging.info(f"job_id: {job_id}")
        pages = node.get("pages", None)
        if pages is None:
            continue

        pages_images = prepare_pages_images(pages, md_info)
        total_pages = len(pages)
        for page_ndx, page in enumerate(pages):
            p2m = Page2Markdown(job_id, page, total_pages, md_info, pages_images)
            p2m.analyse()
            fname_page = p2m.save_page_markdown()
            fnames_pages.append(fname_page)
        md_info[MIFN.LP_I2H_NORMAL] = pages_images

    cur_job_id = job_ids_set.pop()
    md_info[MIFN.LP_CUR_JOB_ID] = cur_job_id
    md_info[MIFN.LP_CUR_JOB_METADATA] = job_metadata
    md_info[MIFN.FNAMES_MD_PAGES] = fnames_pages

    if MIFN.LP_JOB_ID_HISTORY not in md_info:
        md_info[MIFN.LP_JOB_ID_HISTORY] = []
    if cur_job_id not in md_info[MIFN.LP_JOB_ID_HISTORY]:
        md_info[MIFN.LP_JOB_ID_HISTORY].append(cur_job_id)
    md_info.save()


def _dump_images(parser, json_result, md_info):
    out_dir = md_info.get_out_dir()
    images = parser.get_images(json_result, out_dir)
    fnames_imgs = [
        os.path.basename(item["path"])
        for item in images
        if item["name"].startswith("img_")
    ]
    fnames_snps = [
        os.path.basename(item["path"])
        for item in images
        if item["name"].startswith("page_")
    ]
    md_info[MIFN.FNAMES_IMGS] = fnames_imgs
    md_info[MIFN.FNAMES_SNPS] = fnames_snps


def _dump_tables(parser, json_result, md_info):
    out_dir = md_info.get_out_dir()
    tables = parser.get_xlsx(json_result, out_dir)
    fnames_tbls = [os.path.basename(item["path"]) for item in tables]
    md_info[MIFN.FNAMES_MD_TBLS] = fnames_tbls


def _n2u_restore_unique_name_normal_full(md_info):
    new_job_id = md_info.get(MIFN.LP_CUR_JOB_ID)
    unique_job_id = md_info.get_unique_job_id()
    if unique_job_id == new_job_id:
        return

    out_dir = md_info.get_out_dir()
    n2u_replace_fnames(md_info, MIFN.FNAMES_MD_PAGES, unique_job_id, new_job_id)
    n2u_replace_fnames(md_info, MIFN.FNAMES_IMGS, unique_job_id, new_job_id)
    n2u_replace_fnames(md_info, MIFN.FNAMES_MD_TBLS, unique_job_id, new_job_id)
    n2u_replace_fnames(md_info, MIFN.FNAMES_SNPS, unique_job_id, new_job_id)

    for fname_md_page in md_info[MIFN.FNAMES_MD_PAGES]:
        pathname_page = os.path.join(out_dir, fname_md_page)
        n2u_update_md_content(md_info, pathname_page, unique_job_id, new_job_id)


def _dump_json_result(json_result, md_info):
    aux_folder = md_info.get_aux_dir()
    fname_json_result = os.path.join(aux_folder, "json_result_normal.json")

    with open(fname_json_result, "w", encoding="utf-8") as f:
        json.dump(json_result, f, ensure_ascii=False, indent=4)
    md_info[MIFN.LP_FNAME_JSON_RESULT_NORMAL] = fname_json_result


def gen_normal_pages(md_info):
    parser = _get_llamaparse_normal(md_info)

    fname_json_result = md_info.get(MIFN.LP_FNAME_JSON_RESULT_NORMAL, None)
    if fname_json_result is not None and os.path.isfile(fname_json_result):
        with open(fname_json_result, "r", encoding="utf-8") as f:
            json_result = json.load(f)
    else:
        doc_pathname = md_info.get_doc_pathname()
        documents = parser.load_data(doc_pathname)
        if documents is None or len(documents) == 0:
            raise ValueError(f"llamaparse documents is empty for {doc_pathname}")

        json_result = parser.get_json_result(doc_pathname)
        if json_result is None or len(json_result) == 0:
            raise ValueError(f"llamaparse json_result is empty for {doc_pathname}")

        _dump_images(parser, json_result, md_info)
        _dump_tables(parser, json_result, md_info)

    remove_misc_files_previous_round(md_info)
    _dump_json_result(json_result, md_info)

    _dump_normal_md_page_from_lp_json_result(json_result, md_info)

    md_info.save()
    _n2u_restore_unique_name_normal_full(md_info)
    md_info.save()

    return json_result


if __name__ == "__main__":
    setup_logger_handlers()

    md_info_path = "_output/ctn2md_深度学习在视电阻率快速反演中的研究/_info.json"
    md_info = MdInfo(md_info_path)

    ret = gen_normal_pages(md_info)
    rich.print(ret)
