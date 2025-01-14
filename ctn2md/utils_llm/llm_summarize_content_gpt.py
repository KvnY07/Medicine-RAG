from dotenv import load_dotenv
import sys
import os
import logging
import rich 

if "./" not in sys.path:
    sys.path.append("./")
load_dotenv()

from ctn2md.utils_llm.llm_summarize_content_gpt_prompt import SYSTEM_PROMPT_SUMMARIZE, USER_PROMPT_SUMMARIZE
from ctn2md.utils.util_llm_diag import save_llm_diag_messages, set_question_num, get_next_question_num
from ctn2md.utils_llm.llm_base import get_gpt_messages, chat_gpt_json


def summarize_doc_keywords_by_gpt(doc_title, full_content, model="gpt-4o-mini", question_num=None):
    if question_num is None:
        question_num = get_next_question_num()

    try:
        if model not in ["gpt-4o-mini", "gpt-4o"]: 
            raise ValueError(f"f{model} not supporst")

        logging.info(f"start to summarize the content by {model} as question_num: {question_num}")
        prompt = USER_PROMPT_SUMMARIZE.replace("{doc_title}", doc_title).replace("{full_content}", full_content)

        temperature = 0.1
        top_p = 0.9
        messages = get_gpt_messages(SYSTEM_PROMPT_SUMMARIZE, prompt)

        resp = chat_gpt_json(messages, 
                             model=model,
                             temperature=temperature,
                             top_p=top_p,
                             track_id=f"sdk_sum{question_num}")

        set_question_num(question_num)
        save_llm_diag_messages(messages, resp, model=model, temperature=temperature, top_p=top_p, prefix="gvi_vllminst") 

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

    doc_title = "5. back panel 与环境匹配工程校核_P2"
    page_content = """  
<!-- [ordered_name] 1) 前后排座椅间距定义 [ordered_name] [desc] 前后排座椅间距定义 [desc] -->
# 前后排座椅间距定义

金轲 2023-11

适途科技

**目录**


<!-- [ordered_name] 2) 设计要求 [ordered_name] [desc] 设计要求 [desc] -->
# 设计要求


<!-- [ordered_name] 2.1.1) 设计要求 [ordered_name] [desc] 设计要求 __ PL2 __ 设计要求 [desc] -->
### 设计要求

设计的座椅位置的数量 - 中国法规

截图后测量以下参数，看是否满足要求

| 序号 | 描述 | 法规要求 | 设计目标值 |
|---|---|---|---|
| S 9 . 2 | 前后排座椅距离 | ＞ 600.0 mm | 后排座 ＞ 612 mm |
| e | （第一排和第二排或第二排和第三排） | | 椅 |"""


    resp= summarize_doc_keywords_by_gpt(doc_title, page_content)
    rich.print(resp)

