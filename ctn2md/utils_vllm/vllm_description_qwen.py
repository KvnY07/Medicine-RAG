#import time
#import random
import os
#import logging
import sys
#import json
import rich
from dotenv import load_dotenv


if "./" not in sys.path:
    sys.path.append("./")

load_dotenv()

from ctn2md.utils_vllm.vllm_base import chat_qwen_mm


#model='qwen-vl-max-1119'
#model='qwen-vl-max-0809'
def generate_image_description_by_qwen(image_url, instruction=None, model='qwen-vl-max-1119', retries=5, backoff_in_seconds=1):

    if instruction is None:
        instruction = "请简单描述一下这张图片。"
         
    messages = [{
        'role': 'user',
        'content': [
            {
                'image': image_url
            },
            {
                'text': instruction
            },
        ]
    }]
    response = chat_qwen_mm(messages, model=model, retries=retries, backoff_in_seconds=backoff_in_seconds, track_id="gid")
    return response

if __name__ == '__main__':
    from ctn2md.utils.util_file import get_root_dir
    from ctn2md.utils.util_logging import setup_logger_handlers
    from ctn2md.utils_vllm.vllm_description_qwen_prompt import TEXT_PROMPT_INST_VLLM_GEN_QAS

    dir_root = get_root_dir()
    setup_logger_handlers()

    image_url = "datasets/test/images/头枕杆圆角定义/头枕杆圆角定义_img_P10.png"

    full_path = os.path.join(dir_root, image_url)
    container_name = os.path.basename(os.path.dirname(image_url))

    # ret1 = generate_image_description_by_qwen(full_path)
    # print(ret1)
    # print()

    #instruction = f"这是一张在'{container_name}'文件中的图片， 请简单描述一下这张图片。"   
    #ret2 = generate_image_description_by_qwen(full_path, instruction=instruction)
    #print(ret2)
    #print()

    instruction = f"这是一张在'{container_name}'文件中的图片， 请详细描述一下这张图片。 要被用到知识库建设中，所以知识性细节越多越好."   
    ret3 = generate_image_description_by_qwen(full_path, instruction=instruction)
    rich.print(ret3)
    print()

    instruction = TEXT_PROMPT_INST_VLLM_GEN_QAS.replace("{container_name}", container_name)
    ret4 = generate_image_description_by_qwen(full_path, instruction=instruction)
    rich.print(ret4)
    print()