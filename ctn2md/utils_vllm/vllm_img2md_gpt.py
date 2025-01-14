import os
import sys
import logging

import rich
from dotenv import load_dotenv

if "./" not in sys.path:
    sys.path.append("./")
load_dotenv()

from ctn2md.utils_llm.llm_base import chat_gpt_plain, get_gpt_messages_multimodal
from ctn2md.utils.util_llm_diag import (
    set_question_num,
    get_next_question_num,
    save_llm_diag_messages,
)
from ctn2md.utils_vllm.vllm_img2md_gpt_prompt import (
    USER_PROMPT_IMG2MD,
    SYSTEM_PROMPT_IMG2MD,
    USER_PROMPT_INST_IMG_RECTS,
)


def generate_full_mds_from_image_gpt(
    pname_image, rects_img=None, model="gpt-4o", question_num=None
):
    if question_num is None:
        question_num = get_next_question_num()

    try:
        if model not in ["gpt-4o"]:
            raise ValueError(f"f{model} not supporst")
        system_prompt = SYSTEM_PROMPT_IMG2MD

        inst_img_rects = ""
        if rects_img is not None and len(rects_img) > 0:
            str_rects_img = ",".join(rects_img)
            inst_img_rects = USER_PROMPT_INST_IMG_RECTS.replace(
                "{img_rects}", str_rects_img
            )

        user_prompt = USER_PROMPT_IMG2MD.replace("{inst_img_rects}", inst_img_rects)

        temperature = 0.1
        top_p = 0.9
        messages = get_gpt_messages_multimodal(system_prompt, user_prompt, pname_image)

        logging.info(f"GFMFIG: convert pdf page {pname_image} to md by gpt started...")

        resp = chat_gpt_plain(
            messages,
            model=model,
            temperature=temperature,
            top_p=top_p,
            track_id=f"vllm_gpt_{question_num}",
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

        content = resp
        if "```markdown" in content:
            content = content.replace("```markdown\n", "")
            last_backticks_pos = content.rfind("```")
            if last_backticks_pos != -1:
                content = (
                    content[:last_backticks_pos] + content[last_backticks_pos + 3 :]
                )
        # rich.print(content)
        content = content.replace("```", "   ")

        logging.info(f"GFMFIG: convert pdf page {pname_image} to md by gpt done")
        return content
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

    pname_image = "_work/md_pdf_pages/c3c1d78a-page_3_rects.jpg"
    rects_img = ["c3c1d78a-img_3_1.jpg"]

    full_path = os.path.join(dir_root, pname_image)
    container_name = os.path.basename(os.path.dirname(pname_image))

    text = generate_full_mds_from_image_gpt(full_path, rects_img=rects_img)
    rich.print(text)
