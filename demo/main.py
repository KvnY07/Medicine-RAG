import json
import logging

import gradio as gr
from qdrant_client import QdrantClient
from qdrant_client.http import models

from script import *  # 假设 script.py 包含相关的类和函数
from lib.reranker import jina_rerank

# 设置日志配置
logging.basicConfig(
    level=logging.DEBUG,  # 设置日志级别为 DEBUG，这样可以捕获所有的日志信息
    format="%(asctime)s - %(levelname)s - %(message)s",  # 日志格式
    handlers=[logging.StreamHandler()],  # 输出到控制台
)


# Gradio 接口函数
def gradio_interface(query_text, collection_choice):
    logging.info("接收到查询请求.")
    logging.debug(f"查询文本: {query_text}")
    logging.debug(f"选择的集合: {collection_choice}")

    # 选择对应的集合
    if collection_choice == "GMP":
        collection_name = "medicine"
        logging.info("选择了 GMP 集合")
    elif collection_choice == "Guideline":
        collection_name = "medicine_1"
        logging.info("选择了 Guideline 集合")
    else:
        logging.error("无效的集合选择")
        return json.dumps(
            {"error": "Invalid collection choice."}, ensure_ascii=False, indent=2
        )

    # 获取查询向量
    qwen = QWenEmbeddings(batch_size=10)
    logging.info("生成查询向量...")
    query_vector = qwen.get_len_safe_embeddings([query_text])  # 获取查询文本的向量

    # 检查向量是否生成成功
    if not query_vector or not query_vector[0]:
        logging.error("查询向量生成失败")
        return json.dumps(
            {"error": "Error generating query vector."}, ensure_ascii=False, indent=2
        )

    logging.info("查询向量生成成功, 开始进行相似度检索...")

    # 执行相似度检索
    qd_client = QdrantWrapper()
    try:
        result = qd_client.query(collection_name, query_vector[0])  # 查询结果
        logging.info(f"查询成功，返回 {len(result)} 条结果.")
    except Exception as e:
        logging.error(f"查询过程中发生错误: {str(e)}")
        return json.dumps(
            {"error": f"Error querying collection: {str(e)}"},
            ensure_ascii=False,
            indent=2,
        )

    # 格式化查询结果
    formatted_result = []
    if result:
        logging.info(f"开始格式化查询结果...")
        for res in result:
            content = res.payload.get("chunk", "")
            metadata = res.payload.get("metadata", {})
            formatted_result.append(
                {"Content": content[:100] + "...", "Metadata": metadata}  # 显示前 100 字符
            )
    else:
        logging.warning("没有找到匹配的结果")
        formatted_result = {"error": "No matching results found."}

    # 返回查询结果
    logging.info("返回查询结果.")
    return json.dumps(formatted_result, ensure_ascii=False, indent=2)


# 创建 Gradio 界面
with gr.Blocks() as iface:
    gr.Markdown("# 相似度检索与重排序系统")

    # 定义一个状态来存储检索结果
    state = gr.State(value={"query": "", "results": {}})

    with gr.Row():
        with gr.Column(scale=1):
            gr.Markdown("## 相似度检索")
            query = gr.Textbox(label="请输入查询语句", placeholder="输入你的查询语句...")
            collection = gr.Radio(["GMP", "Guideline"], label="请选择集合")
            search_button = gr.Button("开始检索")
            search_output = gr.JSON(label="检索结果")

        with gr.Column(scale=1):
            gr.Markdown("## 重排序")
            rerank_button = gr.Button("开始重排序")
            rerank_output = gr.JSON(label="重排序结果")

    # 定义检索按钮的点击事件
    def search_and_store(query, collection):
        results = gradio_interface(query, collection)
        state = {"query": query, "results": results}
        return results, state  # 返回到 search_output 和 state

    search_button.click(
        fn=search_and_store, inputs=[query, collection], outputs=[search_output, state]
    )

    # 定义重排序按钮的点击事件
    def rerank_and_return(state):
        query = state["query"]
        results = state["results"]
        results = json.loads(results)
        content_list = [v.get("Content", "") for v in results]
        reranked = jina_rerank(query, content_list, top_n=5).get("results", [])
        return reranked

    rerank_button.click(fn=rerank_and_return, inputs=[state], outputs=rerank_output)

if __name__ == "__main__":
    logging.info("启动 Gradio 界面...")
    iface.launch(share=True)
