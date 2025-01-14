import os
import sys

# import random
import json
import logging

import rich
from dotenv import load_dotenv

load_dotenv()

if "./" not in sys.path:
    sys.path.append("./")

from ctn2md.src.md_info_base import MIFN, MdInfo
from ctn2md.utils.util_logging import setup_logger_handlers
from ctn2md.utils.util_markdown import remove_comment, read_markdown_file
from ctn2md.utils_llm.llm_summarize_content_gpt import summarize_doc_keywords_by_gpt
from ctn2md.utils_llm.llm_summarize_content_qwen import summarize_doc_keywords_by_qwen


def summarize_content_by_llm(md_info_path, src_step_num=None, dst_step_num=None):
    logging.info(
        f"##MDFLOW##: summarize_content_by_llm started src_step_num:{src_step_num} dst_step_num:{dst_step_num}..."
    )
    md_info = MdInfo(md_info_path)

    pathname_src_step_md, _ = md_info.name_src_n_dst_step_pathname(
        src_step_num, dst_step_num=dst_step_num
    )
    if pathname_src_step_md is None:
        raise ValueError(f"no {pathname_src_step_md}")

    full_content = read_markdown_file(pathname_src_step_md)
    full_content = remove_comment(full_content)

    doc_title = md_info.get_doc_title()

    # TODO: ethan_bm25,  would be nice if we prepare document level bm25 info (how to cut the word, dictionary etc) as pickle or something structure that able to help calculate the bm25 score without knowing too much
    # especially difference document might have different terms (for word cut in chinese)

    mctl_summarize_model = md_info.get_md_control("mctl_summarize_model", "gpt")
    if mctl_summarize_model == "gpt":
        resp = summarize_doc_keywords_by_gpt(doc_title, full_content)
    elif mctl_summarize_model == "qwen":
        resp = summarize_doc_keywords_by_qwen(doc_title, full_content)
    else:
        raise ValueError(
            f"not implemented yet for using {mctl_summarize_model} in sumamrize document"
        )
    rich.print(resp)

    pathname_final_md_fname = md_info.name_step_pathname(-1)
    pathname_final_json_fname = pathname_final_md_fname.replace(".md", ".sum.json")
    json_str = json.dumps(resp, ensure_ascii=False, indent=4)
    with open(pathname_final_json_fname, "w+", encoding="utf8") as f:
        f.write(json_str)

    md_info[MIFN.FNAME_FINAL_SUM] = os.path.basename(pathname_final_json_fname)
    md_info_path = md_info.save()
    logging.info(f"##MDFLOW##: summarize_content_by_llm ended.")
    return md_info_path


if __name__ == "__main__":
    setup_logger_handlers()

    src_step_num = 2

    # md_info_path = "_output/ctn2md_前后排座椅间距定义 P1/_info.json"
    # md_info_path = "_output/ctn2md_高效沟通之黄金三角模型课程大纲/_info.json"
    md_info_path = "_output/ctn2md_attention_is_all_you_need/_info.json"

    md_info_path = summarize_content_by_llm(md_info_path, src_step_num=src_step_num)
    print(md_info_path)

    md_info = MdInfo(md_info_path)
    rich.print(md_info)
    print(md_info_path)
