import os
import sys
import logging

import rich
from dotenv import load_dotenv

# import random
# import re
# import shutil

load_dotenv()

if "./" not in sys.path:
    sys.path.append("./")

from ctn2md.src.md_info_base import MIFN, MdInfo
from ctn2md.utils.util_logging import setup_logger_handlers
from ctn2md.utils.util_ctn_type import CTN_TYPE
from ctn2md.gen_lp.lp_gen_normal_pages import gen_normal_pages
from ctn2md.gen_lp.lp_gen_premium_pages import gen_premium_pages


def _construct_s0_md_from_pages(md_info):
    out_dir = md_info.get_out_dir()
    aux_dir = md_info.get_aux_dir()
    fnames_pages = md_info[MIFN.FNAMES_MD_PAGES]
    if len(fnames_pages) == 0:
        raise ValueError(f"{MIFN.FNAMES_MD_PAGES} is empty")
    pathname_step0 = md_info.name_step_pathname(0)

    full_md_text = ""
    for fname_page in fnames_pages:
        fname_page = os.path.basename(fname_page)
        pname_page = os.path.join(out_dir, fname_page)
        if not os.path.isfile(pname_page):
            pname_page = os.path.join(aux_dir, fname_page)
            if not os.path.isfile(pname_page):
                raise ValueError(
                    f"not able to find page md for {fname_page} to construct s0 document"
                )
        with open(pname_page, "r") as f:
            md_text = f.read()
        if len(full_md_text) != 0:
            full_md_text += "\n"
        full_md_text += md_text

    with open(pathname_step0, "w+") as f:
        f.write(full_md_text)
    return pathname_step0


def _assign_final_doc_cnt_type(md_info, json_result):
    doc_type = md_info.get_doc_type()
    md_info[MIFN.DOC_CTN_TYPE] = CTN_TYPE.get_ctn_type_by_doc_type(doc_type)
    if json_result is not None and len(json_result) > 0:
        json_result0_pages = json_result[0].get("pages", None)
        if json_result0_pages is not None and len(json_result0_pages) > 0:
            page1 = json_result0_pages[0]
            if page1["page"] == 1:
                page_width = page1["width"]
                page_height = page1["height"]
                if md_info[MIFN.DOC_CTN_TYPE] == CTN_TYPE.PDF:
                    if page_width > page_height:
                        md_info[MIFN.DOC_CTN_TYPE] = CTN_TYPE.PPT
        md_info.save()


def generate_markdown_llamaparse(
    md_info, need_normal_step=True, need_preminum_step=True
):
    doc_pathname = md_info.get_doc_pathname()
    if (doc_pathname is None) or (not os.path.isfile(doc_pathname)):
        raise ValueError(f"doc_pathname is not valid {doc_pathname}")

    out_dir = md_info.get_out_dir()
    os.makedirs(out_dir, exist_ok=True)

    json_result = None
    if need_normal_step:
        json_result = gen_normal_pages(md_info)

    if need_preminum_step:
        mctl_lp_premium_pages = md_info.get_md_control("mctl_lp_premium_pages", None)
        if (mctl_lp_premium_pages is not None) and (len(mctl_lp_premium_pages) != 0):
            gen_premium_pages(md_info)

    pathname_step0 = _construct_s0_md_from_pages(md_info)
    md_info.add_step_into_md_info_mdflow(
        pathname_step0, actor="generate_markdown_llamaparse"
    )
    md_info.save()

    _assign_final_doc_cnt_type(md_info, json_result)

    logging.info(f"original doc: {doc_pathname}")
    logging.info(f"fname_output: {os.path.basename(pathname_step0)}")

    md_info_path = md_info.save()
    return md_info_path


if __name__ == "__main__":
    setup_logger_handlers()

    need_normal_step = False
    need_preminum_step = True

    md_info_path = "_output/ctn2md_深度学习在视电阻率快速反演中的研究/_info.json"

    md_info = MdInfo(md_info_path)

    ret = generate_markdown_llamaparse(
        md_info,
        need_normal_step=need_normal_step,
        need_preminum_step=need_preminum_step,
    )
    rich.print(ret)
