from dotenv import load_dotenv # , find_dotenv
import sys
import rich
#import os
##import pandas as pd
if "./" not in sys.path:
    sys.path.append("./")

load_dotenv()

from ctn2md.utils.util_logging import setup_logger_handlers
from ctn2md.utils_llm.llm_base import chat_gpt_plain, chat_gpt_json, get_gpt_messages
from ctn2md.utils_llm.llm_base import get_dashscope_client

if __name__ == "__main__":
    setup_logger_handlers()

    messages = get_gpt_messages("you are assitant", "hi, who are you ? response in json")

    ret = chat_gpt_plain(messages)
    rich.print(ret)

    ret = chat_gpt_json(messages)
    rich.print(ret)

    client = get_dashscope_client()

    ret = chat_gpt_plain(messages, client=client, model="qwen-plus")
    rich.print(ret)

    ret = chat_gpt_json(messages, client=client, model="qwen-plus")
    rich.print(ret)