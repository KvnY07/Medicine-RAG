import os
import sys
import json
from datetime import datetime

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)

if project_root not in sys.path:
    sys.path.append(project_root)

from utils.jina_reranker import rerank
from md2vdb.utils.qdrant import Qdrant

qdrant = Qdrant()

collection = 'medicine'

query = ['Are the document management provisions, including all the document management matters such as preparation, revision, approval, distribution, retrieval or discard, established?']

results = qdrant.search(collection, query, 10)

rerankeds = rerank(query[0], results)

with open(f'{project_root}/temp/1_output_{datetime.now().date()}.log', 'w', encoding='utf-8') as f:
    for result in results:
        f.write(result)
        f.write('\n----------------------------\n')
    f.write('\n===============================\n')
    for reranked in rerankeds.get('results', []):
        json.dump(reranked, f)
        f.write('\n----------------------------\n')
