import os
import re
import sys
import logging

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)

if project_root not in sys.path:
    sys.path.append(project_root)

from lib.chatgpt import chat
from prompts.load import P_SYS_KEYWORDS_V0, P_USER_KEYWORDS_V0
from scripts.script import *


def get_med_info(med_name):
    collection_name = "THE_KOREAN_PHARMACOPOEIA"

    qwen = QWenEmbeddings(batch_size=10)
    logging.info("药品查询：生成查询向量...")
    query_vector = qwen.get_len_safe_embeddings(med_name)

    if not query_vector or not query_vector[0]:
        logging.error("药品查询：查询向量生成失败")
        return json.dumps(
            {"error": "Error generating query vector."}, ensure_ascii=False, indent=2
        )

    logging.info("药品查询：查询向量生成成功, 开始进行相似度检索...")

    # 执行相似度检索
    qd_client = QdrantWrapper()

    #     filter_conditions = {
    #     "must": [
    #         {"key": "metadata", "match": {"value": collection_name}}
    #     ]
    # }

    try:
        result = qd_client.query(collection_name, query_vector[0], limit=10)  # 查询结果
        logging.info(f"药品查询：查询成功，返回 {len(result)} 条结果.")
    except Exception as e:
        logging.error(f"药品查询：查询过程中发生错误: {str(e)}")
        return json.dumps(
            {"error": f"Error querying collection: {str(e)}"},
            ensure_ascii=False,
            indent=2,
        )

    titles = []

    for res in result:
        metadata = res.payload.get("metadata", {})
        data_title = metadata.get("title", {})
        processed_data_title = (
            " ".join(re.sub(r"[^a-zA-Z\s]", "", data_title).split()).lower().title()
        )
        if processed_data_title == med_name:
            data = res.payload.get("chunk", "")
            return data
        titles.append(processed_data_title)
    return None


def generate_keywords_by_gpt(med_data, log_id=None):
    temperature = 0.1
    top_p = 0.9
    messages = [
        {"role": "system", "content": P_SYS_KEYWORDS_V0},
        {"role": "user", "content": P_USER_KEYWORDS_V0.format(med_info=med_data)},
    ]

    resp = chat(
        model="gpt-4o",
        messages=messages,
        temperature=temperature,
        top_p=top_p,
        seed=42,
        log_id=log_id,
    )

    return resp


if __name__ == "__main__":
    med_name = "Dopamine hydroCHloride 好累想下班 프로필을 기반으로"
    med_name = " ".join(re.sub(r"[^a-zA-Z\s]", "", med_name).split()).lower().title()
    med_data = get_med_info(med_name)
    if med_data:
        result = generate_keywords_by_gpt(med_data)
        print(result)
    else:
        print("fail")

# 输出示例:
#         {
#   "name": "Dopamine Hydrochloride",
#   "type": "General drugs",
#   "nature": "Solid",
#   "usage": "Cardiovascular drugs",
#   "characteristics": [
#     "freely soluble in water",
#     "sparingly soluble in ethanol",
#     "sensitive to light",
#     "requires tight containers",
#     "requires light-resistant storage"
#   ],
#   "keywords": [
#     "General drugs",
#     "Solid dosage forms",
#     "Production processes for solid drugs",
#     "Quality control standards",
#     "Temperature and humidity control",
#     "Storage area isolation requirements",
#     "Protective measures",
#     "Validation requirements",
#     "Cleaning and hygiene management",
#     "Compliance with GMP requirements"
#   ]
# }
