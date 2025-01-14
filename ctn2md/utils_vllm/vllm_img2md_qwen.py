#import time
#import random
import os
import logging
import sys
#import json
import rich
from dotenv import load_dotenv

#import json_repair


if "./" not in sys.path:
    sys.path.append("./")

load_dotenv()

from ctn2md.utils_vllm.vllm_img2md_qwen_prompt import PROMPT_INSTRUCT_IMG2MD_QWEN_START, PROMPT_INSTRUCT_IMG2MD_QWEN_START_IMG_RECTS, PROMPT_INSTRUCT_IMG2MD_QWEN_CONTINUE
from ctn2md.utils_vllm.vllm_base import chat_qwen_mm

def generate_full_mds_from_image_qwen(pname_image, rects_img=None, model='qwen-vl-max-1119', retries=5, backoff_in_seconds=1):
         
    inst_img_rects = ""
    if rects_img is not None and len(rects_img) > 0:
        str_rects_img = ",".join(rects_img)
        inst_img_rects = PROMPT_INSTRUCT_IMG2MD_QWEN_START_IMG_RECTS.replace("{img_rects}", str_rects_img)
    
    prompt_start = PROMPT_INSTRUCT_IMG2MD_QWEN_START.replace("{inst_img_rects}", inst_img_rects)

    messages = [{'role': 'user',
                 'content': [{'image': pname_image}, {'text': prompt_start}]}]
    
    # The model name 'qwen-vl-max-0809' is the identity of 'Qwen2-VL-72B'.
    logging.info(f"GFMFI: generate_full_mds_from_image started... {pname_image}")
    full_content = ""
    for loop in range(4):
        logging.info(f"GFMFI: start loop:{loop}")
        response = chat_qwen_mm(messages, model=model, retries=retries, backoff_in_seconds=backoff_in_seconds, track_id="gfmdiq")
        text_content = response.replace("```markdown", "").replace("```", "")
        full_content += text_content
        if text_content.find("[ocr_end]") != -1:
            logging.info(f"GFMFI: finished [ocr_end] loop@{loop}")
            break
        if response.output.finish_reason:
            logging.info(f"GFMFI: finished finish_reason @{loop}")
            break
        if len(messages) == 1:
            messages.append(
                {'role': response.output.choices[0].message.role,
                 'content': [{'text': text_content}]})
            messages.append(
                {'role': 'user',
                 'content':[{'text': PROMPT_INSTRUCT_IMG2MD_QWEN_CONTINUE}]})
        else:
            messages[1]["content"] = [{'text': full_content}]
    full_content = full_content.replace("[ocr_end]", "")
    #rich.print(messages)
    logging.info(f"GFMFI: total output length {len(full_content)}")
    logging.info(f"GFMFI: generate_full_mds_from_image ended. {pname_image}")
    return full_content


if __name__ == '__main__':
    from ctn2md.utils.util_file import get_root_dir
    from ctn2md.utils.util_logging import setup_logger_handlers
    dir_root = get_root_dir()
    setup_logger_handlers()

    pname_image = "_work/md_samples/e479b909-page_1_rects.png"
    rects_img = ['e479b909-img_1_1.png']

    full_path = os.path.join(dir_root, pname_image)
    container_name = os.path.basename(os.path.dirname(pname_image))

    text = generate_full_mds_from_image_qwen(full_path, rects_img=rects_img)
    rich.print(text)
