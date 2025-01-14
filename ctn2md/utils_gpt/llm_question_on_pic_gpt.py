#import time
#import random
import os
import logging
import sys
#import json
import rich
from dotenv import load_dotenv



if "./" not in sys.path:
    sys.path.append("./")

load_dotenv()

from ctn2md.utils_llm.llm_question_on_pic_gpt_prompt import SYSTEM_PROMPT_GPT4_QAGEN, USER_PROMPT_GPT4_QAGEN
from ctn2md.utils.util_llm_diag import save_llm_diag_messages, set_question_num, get_next_question_num
from ctn2md.utils_llm.llm_base import get_gpt_messages, chat_gpt_json


def gen_questions_on_pic_by_gpt(container_name, img_desc, model="gpt-4o", question_num=None):
    if question_num is None:
        question_num = get_next_question_num()

    try:
        if model not in ["gpt-4o-mini", "gpt-4o"]: 
            raise ValueError(f"f{model} not supporst")
    
        logging.info(f"start to generate questions by {model}...")
        prompt = USER_PROMPT_GPT4_QAGEN.replace("{container_name}", container_name).replace("{img_desc}", img_desc)

        temperature = 0.3
        top_p = 0.95        
        messages = get_gpt_messages(SYSTEM_PROMPT_GPT4_QAGEN, prompt)

        resp = chat_gpt_json(messages, 
                             model=model,
                             temperature=temperature,
                             top_p=top_p,
                             track_id=f"gqo_picdesc_{question_num}")

        set_question_num(question_num)
        save_llm_diag_messages(messages, resp, model=model, temperature=temperature, top_p=top_p, prefix="gqo_picdesc") 
        return resp
    except Exception as ex: 
        logging.exception(ex)
        raise ex

if __name__ == '__main__':
    from ctn2md.utils.util_file import get_root_dir
    from ctn2md.utils.util_logging import setup_logger_handlers
    from ctn2md.utils_vllm.vllm_description_qwen import generate_image_description_by_qwen
    dir_root = get_root_dir()
    setup_logger_handlers()

    image_url = "datasets/test/images/头枕杆圆角定义/头枕杆圆角定义_img_P10.png"

    full_path = os.path.join(dir_root, image_url)
    container_name = os.path.basename(os.path.dirname(image_url))

    instruction = f"这是一张在'{container_name}'文件中的图片， 请详细描述一下这张图片。 要被用到知识库建设中，所以知识性细节越多越好."   
    ret3 = generate_image_description_by_qwen(full_path, instruction=instruction)
    print(ret3)
    print()

    img_desc = ret3
    ret5 = gen_questions_on_pic_by_gpt(container_name, img_desc)
    rich.print(ret5)
    print()