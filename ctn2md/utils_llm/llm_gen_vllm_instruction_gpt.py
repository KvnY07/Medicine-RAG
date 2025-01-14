from dotenv import load_dotenv
import sys
import os
import logging
import rich 

if "./" not in sys.path:
    sys.path.append("./")
load_dotenv()

from ctn2md.utils.util_llm_diag import save_llm_diag_messages, set_question_num, get_next_question_num
from ctn2md.utils_llm.llm_gen_vllm_instruction_gpt_prompt import SYSTEM_PROMPT_GEN_VLLM_CONTEXT, USER_PROMPT_GEN_VLLM_CONTEXT
from ctn2md.utils_llm.llm_base import get_gpt_messages, chat_gpt_json
from ctn2md.utils_vllm.vllm_description_qwen_prompt import TEXT_PROMPT_INST_VLLM_IMG_RELEVANCE


def gen_vllm_instruction_by_gpt(doc_title, page_content, model="gpt-4o-mini", question_num=None):
    if question_num is None:
        question_num = get_next_question_num()

    try:
        if model not in ["gpt-4o-mini", "gpt-4o"]: 
            raise ValueError(f"f{model} not supporst")

        logging.info(f"start to make vllm instruction by {model} as question_num: {question_num}")
        prompt = USER_PROMPT_GEN_VLLM_CONTEXT.replace("{doc_title}", doc_title).replace("{page_content}", page_content)

        temperature = 0.1
        top_p = 0.9
        messages = get_gpt_messages(SYSTEM_PROMPT_GEN_VLLM_CONTEXT, prompt)

        resp = chat_gpt_json(messages, 
                             model=model,
                             temperature=temperature,
                             top_p=top_p,
                             track_id=f"gvi_vllinst_{question_num}")

        set_question_num(question_num)
        save_llm_diag_messages(messages, resp, model=model, temperature=temperature, top_p=top_p, prefix="gvi_vllminst") 

        page_context = resp['page_context']
        page_content_language = resp['page_content_language']

        instruction = TEXT_PROMPT_INST_VLLM_IMG_RELEVANCE.replace("{page_context}", page_context).replace("{page_content_language}",page_content_language)
        return instruction
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
    page_content = """  back panel 与环境匹配工程校核

1
 Restricted © SOTOS 2017. All Rights Reserved."""


    instruction= gen_vllm_instruction_by_gpt(doc_title, page_content)
    rich.print(instruction)

