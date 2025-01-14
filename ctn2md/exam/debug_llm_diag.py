import sys
#import json
import rich
import os
from dotenv import load_dotenv  # , find_dotenv
#import logging
#from collections import OrderedDict
from deepdiff import DeepDiff

load_dotenv()
if './' not in sys.path:
    sys.path.append('./')

from ctn2md.utils.util_file import get_root_dir
from ctn2md.utils.util_llm_diag import load_llm_diag
from ctn2md.utils_llm.llm_base import chat_gpt_json, chat_gpt_plain
from ctn2md.utils.util_logging import setup_logger_handlers

def do_diag_reproduce(llm_diag_pathname):
    messages, answer_old, extra = load_llm_diag(debug_filename)

    top_p = 0.9
    temperature = 0.3
    is_json_respone = True 
    model = "gpt4o"
    if extra is not None:
        top_p = extra.get("top_p", top_p)
        temperature = extra.get("temperature", temperature)
        model = extra.get("model", model)
        is_json_respone = extra.get("is_json_response", is_json_respone)

    if is_json_respone:
        answer_new = chat_gpt_json(messages, model=model, top_p=top_p, temperature=temperature, track_id="llm_ddr_json")
    else:
        answer_new = chat_gpt_plain(messages, model=model, top_p=top_p, temperature=temperature, track_id="llm_ddr_plain")

    rich.print(answer_old)
    print()
    rich.print(answer_new)
    print()

    answer_changed = DeepDiff(answer_old, answer_new)
    rich.print(answer_changed)
    print()
    return answer_old, answer_new, answer_changed

if __name__ == "__main__":
    setup_logger_handlers()
    
    #debug_filename = "_work/md_samples/llm_fhl_heading_q11.txt"
    #debug_filename = "_work/md_samples/llm_gvi_vllminst_q6000.txt"
    debug_filename = "_work/md_samples/llm_gvi_vllminst_q31.txt"

    dir_root = get_root_dir()
    llm_diag_pathname = os.path.join(dir_root, debug_filename)

    do_diag_reproduce(llm_diag_pathname)

