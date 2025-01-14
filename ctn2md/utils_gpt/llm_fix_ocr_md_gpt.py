from dotenv import load_dotenv
import sys
import os
import logging


if "./" not in sys.path:
    sys.path.append("./")
load_dotenv()

from ctn2md.utils_llm.llm_fix_ocr_md_gpt_prompt import SYSTEM_PROMPT_MD_SELF_CORRECT 
from ctn2md.utils_llm.llm_fix_ocr_md_gpt_prompt import USER_PROMPT_MD_SELF_CORRECT_PDF 
from ctn2md.utils_llm.llm_fix_ocr_md_gpt_prompt import USER_PROMPT_MD_SELF_CORRECT_PPT 
from ctn2md.utils_llm.llm_fix_ocr_md_gpt_prompt import USER_PROMPT_MD_SELF_CORRECT_DOC 
from ctn2md.utils.util_ctn_type import CTN_TYPE
from ctn2md.utils.util_llm_diag import save_llm_diag_messages, set_question_num, get_next_question_num
from ctn2md.utils_llm.llm_base import get_gpt_messages, chat_gpt_json


def fix_ocr_self_correct_markdown_by_gpt(md_text, ctn_type, model="gpt-4o-mini", question_num=None):
    if question_num is None:
        question_num = get_next_question_num()

    try:
        if model not in ["gpt-4o-mini", "gpt-4o"]: 
            raise ValueError(f"f{model} not supporst")

        if ctn_type not in [CTN_TYPE.PDF, CTN_TYPE.PPT, CTN_TYPE.DOC]:
            raise ValueError(f"unknown ctn_type {ctn_type}")   
        # if model != "gpt-4o":
        #     raise ValueError(f" ocr is hard, need gpt-4o model only.")
        system_prompt = SYSTEM_PROMPT_MD_SELF_CORRECT
        if ctn_type == CTN_TYPE.PDF:
            user_prompt = USER_PROMPT_MD_SELF_CORRECT_PDF
        elif ctn_type == CTN_TYPE.PPT:
            user_prompt = USER_PROMPT_MD_SELF_CORRECT_PPT
        elif ctn_type == CTN_TYPE.DOC:
            user_prompt = USER_PROMPT_MD_SELF_CORRECT_DOC

        user_prompt = user_prompt.replace("{markdown}", md_text)

        temperature = 0.1
        top_p = 0.9
        messages = get_gpt_messages(system_prompt, user_prompt)

        resp = chat_gpt_json(messages, 
                             model=model,
                             temperature=temperature,
                             top_p=top_p,
                             track_id=f"fox_orc_{question_num}")

        set_question_num(question_num)
        save_llm_diag_messages(messages, resp, model=model, temperature=temperature, top_p=top_p, prefix="fox_ocr") 

        content = resp['content']
        return content
    except Exception as ex: 
        logging.exception(ex)
        raise ex

if __name__ == "__main__":
    from ctn2md.utils.util_logging import setup_logger_handlers
    from ctn2md.utils.util_file import get_root_dir
    setup_logger_handlers()
    dir_root = get_root_dir()
    os.chdir(dir_root)

    md_old = "_work/md_samples/5. back panel 与环境匹配工程校核_P2___pptx_s3.md"
    md_new = "_work/md_samples/5. back panel 与环境匹配工程校核_P2___pptx_s3-new.md"
    ctn_type = CTN_TYPE.PDF

    with open(md_old, 'r', encoding='utf-8') as f:
        md_text = f.read()

    md_text_fixed = fix_ocr_self_correct_markdown_by_gpt(md_text, ctn_type)
    with open(md_new, "w+", encoding='utf-8') as f:
        f.write(md_text_fixed)