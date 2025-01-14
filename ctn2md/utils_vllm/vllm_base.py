import dashscope
import time
import random
import os
import logging
import sys
#import json
#import rich
import csv
from datetime import datetime
from dotenv import load_dotenv, find_dotenv

if "./" not in sys.path:
    sys.path.append("./")

load_dotenv()

dashscope.api_key = os.environ["DASHSCOPE_API_KEY"]

class MonitorContextLVLM:
    c_monitor_filename = None
    c_fname = "ctn_lvlm_monitor.csv" 

    @classmethod
    def _get_monitor_filename(cls):
        if cls.c_monitor_filename is None:
            dir_root = os.path.dirname(find_dotenv())
            dir_logs = os.path.join(dir_root, "logs")
            os.makedirs(dir_logs, exist_ok=True)
            filename = os.path.join(dir_logs, cls.c_fname)
            cls.c_monitor_filename = filename
        return cls.c_monitor_filename

    def __init__(self, messages, model, track_id, attempt):
        self.messages = messages
        self.model = model
        self.track_id = track_id
        self.attempt = attempt

        self.d0 = None
        self.d1 = None
        self.response = None

    def __enter__(self):
        logging.info(f"MonitorContextLVLM enter model:{self.model}")
        self.d0 = time.time()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        logging.info(f"MonitorContextLVLM exit model:{self.model}")
        self.d1 = time.time()
        self._monitor_call(exc_type)

    def _monitor_call(self, exc_type):
        try:
            filename = self._get_monitor_filename()
            dt = self.d1 - self.d0
            dt = round(dt, 2)
            self.d0 = round(self.d0, 2)
            sec_span = round(dt, 2)
            ts0 = datetime.fromtimestamp(self.d0).strftime("%Y%m%d:%H:%M:%S")

            if self.response is not None:
                output = self.response.output
                choice0 = output.choices[0]
                finish_reason = choice0.finish_reason

                usage = self.response.usage
                input_tokens = usage.input_tokens
                output_tokens = usage.output_tokens
                image_tokens = usage.image_tokens

                output_ratio_per_sec = round(float(output_tokens) / sec_span, 2)
                token_per_ms = round((1.0/output_ratio_per_sec) * 1000.0, 2)

                with open(filename, 'a', newline='') as file:
                    writer = csv.writer(file)
                    writer.writerow([ts0, finish_reason, self.model, sec_span, input_tokens, image_tokens, output_tokens, token_per_ms, str(self.track_id), self.attempt])
            else:
                with open(filename, 'a', newline='') as file:
                    writer = csv.writer(file)
                    writer.writerow([ts0, str(exc_type), self.model, sec_span, 0, 0, 0, 0.0, str(self.track_id), self.attempt])

        except Exception as ex:  # noqa
            logging.exception(ex)

def chat_qwen_mm(messages, model='qwen-vl-max-1119', retries=5, backoff_in_seconds=1, track_id=None):
    for attempt in range(retries):
        try:
            with MonitorContextLVLM(messages, model, track_id, attempt) as mc:
                response = dashscope.MultiModalConversation.call(
                    model=model, 
                    messages=messages)
                mc.response = response 
                return response.output.choices[0].message.content[0]["text"]
        except Exception as e:
            logging.exception(e)
            if attempt == retries - 1:
                raise
            sleep_time = backoff_in_seconds * (2**attempt) + random.uniform(0, 1)
            time.sleep(sleep_time)
    return None