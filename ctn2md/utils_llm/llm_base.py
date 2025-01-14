import os
import re
import csv
import sys
import time
import logging
from datetime import datetime

import rich
import openai
import requests
import json_repair
from dotenv import find_dotenv, load_dotenv
from openai import AzureOpenAI

# import json

if "./" not in sys.path:
    sys.path.append("./")
load_dotenv()

"""
| Task            | `temperature`  | `top_p`       | Comment                                                              |
|-----------------|----------------|---------------|----------------------------------------------------------------------|
| SQL Generation  | `0.0` - `0.2`  | `0.9` - `1.0` | Prioritizes precision and correctness in SQL generation.             |
| Analysis        | `0.3` - `0.6`  | `0.85` - `1.0`| Balances logic with some creativity for diverse perspectives.        |
| Report          | `0.5` - `0.7`  | `0.9` - `1.0` | Supports natural, varied language for detailed report writing.       |

"""

DEFAULT_RETRY_NUM = 5


def get_gpt_messages(system_prompt, user_prompt):
    messages = [
        {"role": "system", "content": str(system_prompt)},
        {"role": "user", "content": str(user_prompt)},
    ]
    # messages_str = json.dumps(messages)
    # messages_loaded = json.loads(messages_str)
    return messages


def _generate_unique_name(image_path):
    # 将路径中的文件名提取出来
    filename = re.search(r"[^/\\]*$", image_path).group()

    # 替换掉文件名中的特殊字符
    safe_filename = re.sub(r"[^\w\-_.]", "", filename)

    # 获取当前日期并格式化为YYYYMMDD格式
    current_date = datetime.now().strftime("%Y%m%d")

    # 将日期添加到文件名中
    unique_name = f"{current_date}_{safe_filename}"

    # 返回URL安全的名称
    return unique_name


def _upload_image(image_path):
    import oss2

    access_key_id = os.environ["OSS_ACCESS_KEY_ID"]
    access_key_secret = os.environ["OSS_ACCESS_KEY_SECRET"]
    endpoint = os.environ["OSS_ENDPOINT"]  # 例如：'https://oss-cn-hangzhou.aliyuncs.com'
    bucket_name = os.environ["OSS_BUCKET_NAME"]  # '<your-bucket-name>'

    logging.info(f"upload {image_path} to oss")
    # 初始化OSS存储
    auth = oss2.Auth(access_key_id, access_key_secret)
    bucket = oss2.Bucket(auth, endpoint, bucket_name)

    # 上传文件
    def upload_file(file_path, object_name):
        with open(file_path, "rb") as file:
            # 设置Content-Disposition为inline，使得文件在浏览器中直接打开
            bucket.put_object(
                object_name, file, headers={"Content-Disposition": "inline"}
            )

    # 调用示例
    object_name = _generate_unique_name(image_path)
    upload_file(image_path, object_name)

    url = bucket.sign_url("GET", object_name, 3600)

    logging.info(f"url:{url} to access upload {image_path} in oss")
    return url


def get_gpt_messages_multimodal(system_prompt, user_prompt, image_path):
    """生成支持多模态的消息结构"""
    img_url = _upload_image(image_path)

    # 构造多模态消息
    messages = [
        {"role": "system", "content": [{"type": "text", "text": str(system_prompt)}]},
        {
            "role": "user",
            "content": [
                {"type": "text", "text": str(user_prompt)},
                {"type": "image_url", "image_url": {"url": img_url}},  # 明确指定类型为 image
            ],
        },
    ]

    return messages


def get_azure_gpt_client():
    client = AzureOpenAI(
        api_key=os.getenv("OPENAI_API_KEY"),
        azure_endpoint=os.getenv("OPENAI_BASE_URL"),
        api_version=os.environ.get("AZURE_OPENAI_VERSION"),
    )
    return client


def get_dashscope_client():
    from openai import OpenAI

    client = OpenAI(
        api_key=os.getenv("DASHSCOPE_API_KEY"),
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
    )
    return client


def jsons_load_repair(content):
    resp = json_repair.repair_json(content, ensure_ascii=True, return_objects=True)
    return resp


class MonitorContextLLM:
    c_monitor_filename = None
    c_fname = "ctn_llm_monitor.csv"

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
        logging.info(f"MonitorContextLLM enter model:{self.model}")
        self.d0 = time.time()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        logging.info(f"MonitorContextLLM enter model:{self.model}")
        self.d1 = time.time()
        self._monitor_call(exc_type)

    def _monitor_call(self, exc_type):
        try:
            filename = self._get_monitor_filename()

            # d0 = response.created
            dt = self.d1 - self.d0
            dt = round(dt, 2)
            self.d0 = round(self.d0, 2)
            sec_span = round(dt, 2)
            ts0 = datetime.fromtimestamp(self.d0).strftime("%Y%m%d:%H:%M:%S")

            model = self.model
            if self.response is not None:
                choice0 = self.response.choices[0]
                finish_reason = choice0.finish_reason

                model = self.response.model

                usage = self.response.usage
                prompt_tokens = usage.prompt_tokens
                total_tokens = usage.total_tokens
                completion_tokens = usage.completion_tokens

                output_ratio_per_sec = round(float(completion_tokens) / sec_span, 2)
                token_per_ms = round((1.0 / output_ratio_per_sec) * 1000.0, 2)

                with open(filename, "a", newline="") as file:
                    writer = csv.writer(file)
                    writer.writerow(
                        [
                            ts0,
                            finish_reason,
                            model,
                            sec_span,
                            total_tokens,
                            prompt_tokens,
                            completion_tokens,
                            token_per_ms,
                            str(self.track_id),
                            self.attempt,
                        ]
                    )
            else:
                with open(filename, "a", newline="") as file:
                    writer = csv.writer(file)
                    writer.writerow(
                        [
                            ts0,
                            str(exc_type),
                            model,
                            sec_span,
                            0,
                            0,
                            0,
                            0.0,
                            str(self.track_id),
                            self.attempt,
                        ]
                    )

        except Exception as ex:  # noqa
            logging.exception(ex)


def chat_gpt_json(
    messages,
    model="gpt-4o-mini",
    temperature=0.1,
    top_p=0.9,
    retries=DEFAULT_RETRY_NUM,
    backoff_factor=2,
    backoff_sec=1,
    delay_base_sec=5,
    track_id=None,
    client=None,
):
    if client is None:
        client = get_azure_gpt_client()
    for attempt in range(retries):
        try:
            with MonitorContextLLM(messages, model, track_id, attempt) as mc:
                response = client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    top_p=top_p,
                    response_format={"type": "json_object"},
                )
                mc.response = response
                resp = jsons_load_repair(response.choices[0].message.content)
                return resp
        except (
            requests.exceptions.RequestException,
            ValueError,
            openai.RateLimitError,
        ) as e:
            if isinstance(e, openai.RateLimitError):
                delay_base_sec += 10
            else:
                logging.error(f"Error on attempt {attempt+1}: {str(e)}")
            if attempt == retries:
                raise
            backoff_sec = backoff_factor**attempt + delay_base_sec
            logging.info(f"Retrying after backoff: {backoff_sec} seconds...")
            time.sleep(backoff_sec)
        except (openai.BadRequestError) as e:
            logging.exception(e)
            raise


def chat_gpt_plain(
    messages,
    model="gpt-4o-mini",
    temperature=0.1,
    top_p=0.9,
    retries=DEFAULT_RETRY_NUM,
    backoff_factor=2,
    backoff_sec=1,
    delay_base_sec=5,
    track_id=None,
    client=None,
):
    if client is None:
        client = get_azure_gpt_client()
    for attempt in range(retries):
        try:
            with MonitorContextLLM(messages, model, track_id, attempt) as mc:
                response = client.chat.completions.create(
                    model=model, messages=messages, temperature=temperature, top_p=top_p
                )
                mc.response = response
                return response.choices[0].message.content
        except (
            requests.exceptions.RequestException,
            ValueError,
            openai.RateLimitError,
        ) as e:
            if isinstance(e, openai.RateLimitError):
                delay_base_sec += 10
            else:
                logging.error(f"Error on attempt {attempt+1}: {str(e)}")
            if attempt == retries:
                raise
            backoff_sec = backoff_factor**attempt + delay_base_sec
            logging.info(f"Retrying after backoff: {backoff_sec} seconds...")
            time.sleep(backoff_sec)
        except (openai.BadRequestError) as e:
            logging.exception(e)
            raise


if __name__ == "__main__":
    messages = get_gpt_messages("", "hi, response in json")
    resp = chat_gpt_json(messages=messages, model="gpt-4o")
    rich.print(resp)

    messages = get_gpt_messages("", "hi, response in json")
    resp = chat_gpt_json(messages=messages, model="gpt-4o-mini")
    rich.print(resp)

    messages = get_gpt_messages("", "hi, response in text")
    resp = chat_gpt_plain(messages=messages, model="gpt-4o")
    rich.print(resp)

    messages = get_gpt_messages("", "hi, response in text")
    resp = chat_gpt_plain(messages=messages, model="gpt-4o-mini")
    rich.print(resp)
