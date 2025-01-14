import os
import sys
import logging

import rich
from dotenv import load_dotenv

# import random
# import json
# import shutil

load_dotenv()

if "./" not in sys.path:
    sys.path.append("./")

if __name__ == "__main__":
    from dotenv import find_dotenv

    _root_dir = os.path.abspath(os.path.dirname(find_dotenv()))
    os.chdir(_root_dir)

from ctn2md.src.md_info_base import MdInfo
from ctn2md.utils.util_logging import setup_logger_handlers
from ctn2md.src.make_final_result import reset_md_flow, make_final_json
from ctn2md.src.ctn2md_gen_md_plain import GenMd_Plain
from ctn2md.src.ctn2md_fix_heading_plc import fix_headings_plc_by_llm
from ctn2md.src.ctn2md_summarize_content import summarize_content_by_llm
from ctn2md.src.ctn2md_inject_section_hierarchy import inject_section_heirarchy


def _do_content2md_convert_core_md(
    doc_pathname, out_dir=None, enforced_gen=False, mdcontrols=None
):
    if out_dir is None:
        out_dir = MdInfo.get_suggested_out_dir(
            doc_pathname, suffix=GenMd_Plain.OD_SUFFIX
        )
    logging.warning(f"work out_dir: {out_dir}")
    os.makedirs(out_dir, exist_ok=True)

    md_generator = GenMd_Plain
    if md_generator is None:
        logging.error("")
        return None

    md_info_path = md_generator.generate_markdown(
        doc_pathname, out_dir=out_dir, enforced_gen=enforced_gen, mdcontrols=mdcontrols
    )
    if md_info_path is None:
        logging.error(f"DCCCM: failed {md_info_path} @initial_gen_md_by_llamaparse")
        return None

    reset_md_flow(md_info_path)

    src_step_num = 0
    if md_generator.need_followup_step("fix_headings_plc_by_llm"):
        md_info_path = fix_headings_plc_by_llm(md_info_path, src_step_num=src_step_num)
        if md_info_path is None:
            logging.error(f"DCCCM: failed {md_info_path} @fix_headings_plc_by_llm")
            return None

    src_step_num += 1
    md_info_path = inject_section_heirarchy(md_info_path, src_step_num=src_step_num)
    if md_info_path is None:
        logging.error(f"DCCCM: failed {md_info_path} @inject_section_heirarchy")
        return None

    src_step_num += 1
    md_info_path = summarize_content_by_llm(md_info_path, src_step_num=src_step_num)
    if md_info_path is None:
        logging.error(f"DCCCM: failed {md_info_path} @summarize_content_by_llm")
        return None

    pathname_final_json = make_final_json(md_info_path)

    return pathname_final_json


def do_content2md_convert(
    doc_pathname, out_dir=None, enforced_gen=False, mdcontrols=None
):
    pathname_final_json = None
    try:
        pathname_final_json = _do_content2md_convert_core_md(
            doc_pathname,
            out_dir=out_dir,
            enforced_gen=enforced_gen,
            mdcontrols=mdcontrols,
        )
    except Exception as ex:
        logging.exception(ex)
        raise ex
    return pathname_final_json


if __name__ == "__main__":
    setup_logger_handlers()

    # doc_pathname = "_output/ctn2md_深度学习在视电阻率快速反演中的研究_lp/深度学习在视电阻率快速反演中的研究___pdf.md"
    doc_pathname = (
        "_output/ctn2md_0530_大模型微调培训_VisualGLM_lp/0530-大模型微调培训-VisualGLM___pdf.md"
    )

    out_dir = None
    mdcontrols = None
    enforced_gen = False

    pathname_final_json = do_content2md_convert(
        doc_pathname, out_dir=out_dir, enforced_gen=enforced_gen, mdcontrols=mdcontrols
    )
    print(pathname_final_json)

    md_info = MdInfo(pathname_final_json)
    rich.print(md_info)
    print(pathname_final_json)
