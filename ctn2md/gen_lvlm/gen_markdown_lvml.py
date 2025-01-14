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
from ctn2md.utils.util_markdown import read_markdown_file
from ctn2md.gen_lvlm.lvlm_gen_pages import gen_pages_lvlm


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
        md_text = read_markdown_file(pname_page)
        if len(full_md_text) != 0:
            full_md_text += "\n"
        full_md_text += md_text

    with open(pathname_step0, "w+") as f:
        f.write(full_md_text)
    return pathname_step0


def generate_markdown_lvlm(md_info, lvlm_model="gpt-4o"):
    doc_pathname = md_info.get_doc_pathname()
    if (doc_pathname is None) or (not os.path.isfile(doc_pathname)):
        raise ValueError(f"doc_pathname is not valid {doc_pathname}")

    out_dir = md_info.get_out_dir()
    os.makedirs(out_dir, exist_ok=True)

    gen_pages_lvlm(md_info)

    pathname_step0 = _construct_s0_md_from_pages(md_info)
    md_info.add_step_into_md_info_mdflow(
        pathname_step0, actor=f"generate_markdown_lvlm@{lvlm_model}"
    )
    md_info.save()

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

    ret = generate_markdown_lvlm(md_info)
    rich.print(ret)
