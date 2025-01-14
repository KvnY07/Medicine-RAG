import re
import os 
import sys
import numpy as np
import logging
import json
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams

current_dir = os.path.dirname(os.path.abspath(__file__))
md2vdb_path = os.path.dirname(current_dir)
project_root = os.path.dirname(md2vdb_path)

if project_root not in sys.path:
    sys.path.append(project_root)

from utils.jina_reranker import rerank
from scripts.script import *

def split_text_to_max_length(text:str):
    max_length = 512
    
    words = text.split()
    
    # 根据最大单词数分组
    chunks = []
    for i in range(0, len(words), max_length):
        chunk = words[i:i + max_length]  # 提取当前分组
        chunks.append(" ".join(chunk))
    
    return chunks


class Qdrant:
    def __init__(self):
        self.client = QdrantClient(host="localhost", port=6333)

    def create_collection(self ,collection_name ,vector_dimension = 1536):
        try:
            self.client.get_collection(collection_name)
            return "该向量库已存在"
        except:
            self.client.recreate_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=vector_dimension, distance=Distance.COSINE)
            )
            return "成功创建向量库"

    def upsert_data(self ,data:list ,collection_name):
        #服务器上的THE_KOREAN_PHARMACOPOEIA数据集用这个方法导入
        #优先使用scripts/script.py的导入方法
        self.client.upsert(
            collection_name=collection_name ,
            points=data
        )
        return "成功导入数据"

    def search(self, collection, text, limit = 5):
        batch_size = 10
        qwen = QWenEmbeddings(batch_size)
        vectors = qwen.get_len_safe_embeddings(text)

        qd_client = QdrantWrapper()
        results = qd_client.query(collection, vectors[0], limit)
        output = []
        for result in results:
            output.append(result.payload['chunk'])
        
        return output
        
        

def md_to_chunk(md_path):
    with open(md_path ,'r' ,encoding = 'utf-8') as f:
        content = f.read()
        
        parts = re.split(r'(?m)^# ', content)
        headlines = re.findall(r'(?m)^# (.+)', content)
        
        sections = [f"# {part}" if i != 0 else part for i, part in enumerate(parts)]
        
        sections = [section.strip() for section in sections if section.strip()]
        
        print(sections)
        
        qwen = QWenEmbeddings(batch_size=10)
        logging.info("生成查询向量...")
        
        embedded_sections = []
        
        for section in sections:
            parts = split_text_to_max_length(section)        
            embedded_texts = qwen.get_len_safe_embeddings(parts)
            pooled_text = np.mean(embedded_texts, axis=0)
            pooled_text = pooled_text.tolist()
            embedded_sections.append(pooled_text)
            
        # points = []
        # for headline ,text in zip(headlines ,embedded_texts):
        #     point ={
        #         "headline" : headline,
        #         "text" : text
        #     }
        #     points.append(point)
        
        
        points = []
        for headline ,embedded_text ,index, text in zip(headlines ,embedded_sections ,range(1,len(headlines)+1), sections):
            point ={
                "id" : index,
                "vector" : embedded_text,
                "payload" : {"chunk": text, "metadata" : {"title" : headline}}
            }
            points.append(point)
        
        return points
    
    
if __name__ == "__main__":
    
    md_path = 'hanyaodian_3_5.md'
    
    data_points = md_to_chunk(md_path)
    
    # demo_data_points = [
    # {
    #     "id": 1,
    #     "vector": np.random.rand(1536).tolist(),
    #     "payload": {"category": "A", "value": 100}
    # },
    # {
    #     "id": 2,
    #     "vector": np.random.rand(1536).tolist(),
    #     "payload": {"category": "B", "value": 200}
    # }
    # ]


    
    with open("test.txt" ,"w" ,encoding= "utf-8") as f:
        json_string = json.dump(data_points[0] ,f)
        # f.write("-----------------------------------------------")
        # json_string = json.dump(demo_data_points[0] ,f)
    
    # for i in text:
    #     print(i)
    
    # for i in range(3):
    #     print(data_points[i])
    #     print("--------------------------------------------")
    #     print("--------------------------------------------")
    #     print("--------------------------------------------")
    

    
    qdrant = Qdrant()
    res = qdrant.upsert_data(data_points ,"THE_KOREAN_PHARMACOPOEIA")
    print(res)