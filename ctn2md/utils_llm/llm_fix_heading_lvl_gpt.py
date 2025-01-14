from dotenv import load_dotenv
import sys
import os
import logging
import rich
import json
#import time


if "./" not in sys.path:
    sys.path.append("./")
load_dotenv()

from ctn2md.utils_llm.llm_fix_heading_lvl_gpt_prompt import SYSTEM_PROMPT_FIX_HEADING_LVL_LOW, USER_PROMPT_FIX_HEADING_LVL_LOW 
from ctn2md.utils_llm.llm_fix_heading_lvl_gpt_prompt import SYSTEM_PROMPT_FIX_HEADING_LVL_NORMAL, USER_PROMPT_FIX_HEADING_LVL_NORMAL
from ctn2md.utils.util_llm_diag import save_llm_diag_messages, set_question_num, get_next_question_num
from ctn2md.utils_llm.llm_base import get_gpt_messages, chat_gpt_json
from ctn2md.utils.util_ctn_type import CTN_TYPE
from ctn2md.src.md_info_base import FHL_QUALITY_TYPE

def fix_heading_lvl_markdown_by_gpt(fhl_org, fhl_quality=FHL_QUALITY_TYPE.LOW, ctn_type=CTN_TYPE.PDF, model="gpt-4o",  question_num=None):
    if question_num is None:
        question_num = get_next_question_num()

    try:
        if model not in ["gpt-4o-mini", "gpt-4o"]: 
            raise ValueError(f"{model} not supporst")

        if not isinstance(fhl_org, dict):
            raise ValueError("fhl_heading need to be dict")

        logging.info(f"start to correct heading level by {model} as question_num:{question_num}")

        fhl_org_json_str = json.dumps(fhl_org, ensure_ascii=False, indent=4)

        user_prompt = USER_PROMPT_FIX_HEADING_LVL_LOW
        if fhl_quality != FHL_QUALITY_TYPE.LOW:
            user_prompt = USER_PROMPT_FIX_HEADING_LVL_NORMAL
        user_prompt = user_prompt.replace("{fhl_org_json_str}", fhl_org_json_str).replace("{ctn_type}", ctn_type)

        system_prompt = SYSTEM_PROMPT_FIX_HEADING_LVL_LOW
        if fhl_quality != FHL_QUALITY_TYPE.LOW:
            system_prompt = SYSTEM_PROMPT_FIX_HEADING_LVL_NORMAL      

        temperature = 0.1
        top_p = 0.95
        messages = get_gpt_messages(system_prompt, user_prompt)

        resp = chat_gpt_json(messages, 
                             model=model,
                             temperature=temperature,
                             top_p=top_p,
                             track_id=f"fhl_heading_{question_num}")

        set_question_num(question_num)
        save_llm_diag_messages(messages, resp, model=model, temperature=temperature, top_p=top_p, prefix="fhl_heading") 

        return resp
    except Exception as ex: 
        logging.exception(ex)
        raise ex

if __name__ == "__main__":
    from ctn2md.utils.util_file import get_root_dir
    from ctn2md.utils.util_logging import setup_logger_handlers
    setup_logger_handlers()
    dir_root = get_root_dir()
    os.chdir(dir_root)

    fhl_org = {
        "org_doc_title": "业绩案例、比亚迪SJ项目低压线束设计技术服务合同（电子电器）",
        "org_first_line": "# 技术服务合同",
        "org_heading_lines": [
            [
                "# 技术服务合同",
                "Page:1/3, Line:1/7, Chars:0/25"
            ],
            [
                "# 比亚迪汽车工业有限公司",
                "Page:1/3, Line:3/7, Chars:0/25"
            ],
            [
                "# 上海适途汽车技术有限公司",
                "Page:2/3, Line:2/7, Chars:0/25"
            ],
            [
                "# 技术服务合同V5.0",
                "Page:2/3, Line:4/7, Chars:0/25"
            ],
            [
                "# 1 工作划分",
                "Page:3/3, Line:1/7, Chars:0/25"
            ],
            [
                "# 2 合同工作的执行",
                "Page:3/3, Line:1/7, Chars:0/25"
            ],
            [
                "# 技术服务合同V5.0",
                "Page:3/3, Line:1/7, Chars:0/25"
            ]
        ]
    }
    new_fhl = fix_heading_lvl_markdown_by_gpt(fhl_org)
    rich.print(new_fhl)