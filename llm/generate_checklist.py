import os
import sys
import logging

_cur_dir = os.path.split(os.path.abspath(__file__))[0]
_prj_dir = os.path.split(_cur_dir)[0]
_root_dir = os.path.split(_prj_dir)[0]
sys.path.append(_root_dir)

from lib.chatgpt import chat
from prompts.load import P_SYS_CHECKLIST_V0, P_USER_CHECKLIST_V0
from scripts.script import *
from utils.jina_reranker import rerank
from utils.tencent_translate import tencent_translate_en2zh


def get_gmp_info(query: str):
    collection_name = "GMP_with_title"
    query_list = [query]
    qwen = QWenEmbeddings(batch_size=10)
    logging.info("GMP查询：生成查询向量...")
    query_vector = qwen.get_len_safe_embeddings(query_list)

    if not query_vector or not query_vector[0]:
        logging.error("GMP查询：查询向量生成失败")
        return json.dumps(
            {"error": "Error generating query vector."}, ensure_ascii=False, indent=2
        )

    logging.info("GMP查询：查询向量生成成功, 开始进行相似度检索...")

    # 执行相似度检索
    qd_client = QdrantWrapper()

    #     filter_conditions = {
    #     "must": [
    #         {"key": "metadata", "match": {"value": collection_name}}
    #     ]
    # }

    try:
        result = qd_client.query(collection_name, query_vector[0], limit=10)  # 查询结果
        logging.info(f"GMP查询：查询成功，返回 {len(result)} 条结果.")
    except Exception as e:
        logging.error(f"GMP查询：查询过程中发生错误: {str(e)}")
        return json.dumps(
            {"error": f"Error querying collection: {str(e)}"},
            ensure_ascii=False,
            indent=2,
        )

    results = []
    for item in result:
        chunk = item.payload.get("chunk", "")
        if chunk:
            results.append(chunk)

    if results:

        reranked = rerank(query, results, top_n=2).get("results", [])

    else:
        logging.error(f"GMP查询：未得到查询结果")
        return json.dumps({"error": "Error querying collection"})

    datas = []
    for res in reranked:
        data = res.get("document", "").get("text", "")
        datas.append(data)
    return datas


def generate_checklist_by_gpt(gmp_data, chara, log_id: str | int | None = None):
    gmp_data = str(gmp_data)
    chara = str(chara)

    temperature = 0.1
    top_p = 0.9
    messages = [
        {"role": "system", "content": P_SYS_CHECKLIST_V0},
        {
            "role": "user",
            "content": P_USER_CHECKLIST_V0.format(gmp_data=gmp_data, chara=chara),
        },
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

    characteristics = {
        "name": "Dopamine Hydrochloride",
        "type": "general",
        "nature": "solid",
        "usage": "cardiovascular drugs",
        "characteristics": [
            "freely soluble in water",
            "sparingly soluble in ethanol",
            "sensitive to light",
            "requires tight containers",
            "requires light-resistant containers",
            "melting point around 248°C with decomposition",
            "requires specific pH range (4.0-5.5)",
            "requires purity tests for sulfates, heavy metals, arsenic, and related substances",
            "requires loss on drying test",
            "requires residue on ignition test",
        ],
    }

    # query = 'Are the document management provisions, including all the document management matters such as preparation, revision, approval, distribution, retrieval or discard, established?'

    gmp_datas = []

    # gmp_datas = []

    # for i in range(len(keywords)):
    #     gmp_data = get_gmp_info(keywords[i])
    #     gmp_datas.append(gmp_data)

    # gmp_data = get_gmp_info(query)
    date = datetime.now().date()

    # with open(f'{project_root}/llm/output/generate_checklist_output-{date}.txt', "a", encoding='utf-8') as f:
    #         json.dump(gmp_data, f)
    #         f.write('\n----------------------\n')

    questions = [
        "Are the document management provisions, including all the document management matters such as preparation, revision, approval, distribution, retrieval or discard, established?",
        "Are documents prepared in a readable form, and signed and dated by the head of the production department or the quality unit?",
        "Personnel who prepares, reviews, and approves documents should register his/her signature prior to use.",
        "Are all records made at the time each action is taken and recorded in indelible ink?",
        "If any entries are corrected, is a line drawn on the letters or sentences to be corrected so that prior contents can be easily seen?",
        "Does the corrected document show the reason for the correction, the corrected date, and the signature of the person who corrected the entries?",
        "When a document is to be revised, is the reason and the date for such revision recorded and is the revised document approved by the head of the production department or the quality unit(s)?",
        "Are the documents checked regularly to confirm whether they are revised lately? Is the previous version retained for an appropriate period?",
    ]

    for query in questions:
        gmp_datas = get_gmp_info(query)

        result = generate_checklist_by_gpt(gmp_datas, characteristics)

        with open(
            f"{project_root}/llm/output/generate_checklist_output-{date}.log",
            "a",
            encoding="utf-8",
        ) as f:
            f.write("\n===========================================================\n")
            f.write(str(datetime.now()))
            f.write(f"\n输入的问题：\n{query}\n")
            f.write(tencent_translate_en2zh(query))
            f.write("\n===========================================================\n")
            f.write("\ngmp召回内容：\n")
            for gmp_data in gmp_datas:
                json_str_gmp = json.dumps(gmp_data, ensure_ascii=False, indent=4)
                f.write(json_str_gmp.replace("\\n", "\n"))
                f.write("\n")
                f.write(tencent_translate_en2zh(json_str_gmp))
                f.write("\n")
                f.write(
                    "\n-----------------------------------------------------------\n"
                )
            f.write("\n===========================================================\n")
            json_str = json.dumps(result, ensure_ascii=False, indent=4)
            f.write("\nllm生成的checklist：\n")
            f.write(json_str.replace("\\n", "\n"))
            f.write("\n")
            f.write(tencent_translate_en2zh(json_str))
            f.write(
                "\n===========================================================\n\n\n\n"
            )

    print("done!")
