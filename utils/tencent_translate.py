import os
import json
import types
import time

from dotenv import load_dotenv
from tencentcloud.common import credential
from tencentcloud.tmt.v20180321 import models, tmt_client
from tencentcloud.common.profile.http_profile import HttpProfile
from tencentcloud.common.profile.client_profile import ClientProfile
from tencentcloud.common.exception.tencent_cloud_sdk_exception import (
    TencentCloudSDKException,
)

load_dotenv()

secretId = os.getenv("TENCENT_CLOUD_SECRETID")
secretKey = os.getenv("TENCENT_CLOUD_SECRETKEY")


def en2zh_core(text):
    try:
        cred = credential.Credential(secretId, secretKey)
        # 实例化一个http选项，可选的，没有特殊需求可以跳过
        httpProfile = HttpProfile()
        httpProfile.endpoint = "tmt.tencentcloudapi.com"

        # 实例化一个client选项，可选的，没有特殊需求可以跳过
        clientProfile = ClientProfile()
        clientProfile.httpProfile = httpProfile
        # 实例化要请求产品的client对象,clientProfile是可选的
        client = tmt_client.TmtClient(cred, "ap-shanghai", clientProfile)

        # 实例化一个请求对象,每个接口都会对应一个request对象
        req = models.TextTranslateBatchRequest()
        params = {
            "Source": "en",
            "Target": "zh",
            "ProjectId": 0,
            "SourceTextList": [text],
        }
        req.from_json_string(json.dumps(params))

        # 返回的resp是一个TextTranslateBatchResponse的实例，与请求对象对应
        resp = client.TextTranslateBatch(req)
        time.sleep(0.2)
        # 输出json格式的字符串回包
        return resp

    except TencentCloudSDKException as err:
        return err


def tencent_translate_en2zh(text):
    # 单次翻译长度需低于6000字符(未完成)
    translated_text = en2zh_core(text)
    return translated_text.TargetTextList[0]


def split_text(text, max_length=20):
    import re

    # 按英文的句子结束符（. ? !）切分文本，同时保留分隔符
    sentences = re.split(r"(?<=[.!?])\s*", text)
    parts = []  # 存储结果的部分
    current_part = ""

    for sentence in sentences:
        # 如果当前部分加上新的句子不会超过最大长度，就加上
        if len(current_part) + len(sentence) <= max_length:
            current_part += sentence + " "  # 注意保留句子之间的空格
        else:
            # 当前部分已满，保存并开启新部分
            parts.append(current_part.strip())
            current_part = sentence + " "

    # 保存最后剩余的部分
    if current_part.strip():
        parts.append(current_part.strip())

    return parts


if __name__ == "__main__":
    text = "Are the document management provisions, including all the document management matters such as preparation, revision, approval, distribution, retrieval or discard, established?"
    result = tencent_translate_en2zh(text)
    print(result)
