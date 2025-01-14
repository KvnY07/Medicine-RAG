import os
import sys
import logging

import rich
from dotenv import load_dotenv

if "./" not in sys.path:
    sys.path.append("./")
load_dotenv()

from ctn2md.utils_llm.llm_base import chat_gpt_json, get_gpt_messages_multimodal
from ctn2md.utils.util_llm_diag import (
    set_question_num,
    get_next_question_num,
    save_llm_diag_messages,
)
from ctn2md.utils_vllm.vllm_img2region_gpt_prompt import (
    USER_PROMPT_IMG2REGION,
    SYSTEM_PROMPT_IMG2REGION,
)


def generate_regions_from_image_gpt(pname_image, model="gpt-4o", question_num=None):
    if question_num is None:
        question_num = get_next_question_num()

    try:
        if model not in ["gpt-4o"]:
            raise ValueError(f"f{model} not supporst")

        system_prompt = SYSTEM_PROMPT_IMG2REGION
        user_prompt = USER_PROMPT_IMG2REGION

        temperature = 0.1
        top_p = 0.9
        messages = get_gpt_messages_multimodal(system_prompt, user_prompt, pname_image)

        logging.info(
            f"GRFIG: convert pdf page {pname_image} to regions by gpt started..."
        )

        resp = chat_gpt_json(
            messages,
            model=model,
            temperature=temperature,
            top_p=top_p,
            track_id=f"vllm_gpt_i2r_{question_num}",
        )

        set_question_num(question_num)
        save_llm_diag_messages(
            messages,
            resp,
            model=model,
            temperature=temperature,
            top_p=top_p,
            prefix="vllm_gpt",
        )
        # rich.print(resp)

        logging.info(f"GRFIG: convert pdf page {pname_image} to regions by gpt done")
        return resp
    except Exception as ex:
        logging.exception(ex)
        raise ex


if __name__ == "__main__":
    from ctn2md.utils.util_file import get_root_dir
    from ctn2md.utils.util_logging import setup_logger_handlers

    dir_root = get_root_dir()
    setup_logger_handlers()

    # pname_image = "_work/md_samples/e479b909-page_1_rects.png"
    # rects_img = ['e479b909-img_1_1.png']
    # rects_img = None

    # pname_image = "_work/md_pdf_pages/c3c1d78a-page_3_rects.jpg"
    pname_image = "_work/md_pdf_pages/bd72132b-page_3.jpg"

    full_path = os.path.join(dir_root, pname_image)
    container_name = os.path.basename(os.path.dirname(pname_image))

    resp = generate_regions_from_image_gpt(full_path)
    rich.print(resp)
