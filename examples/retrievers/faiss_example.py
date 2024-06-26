#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
# https://deepnote.com/blog/semantic-search-using-faiss-and-mpnet
@author: yanqiangmiffy
@contact:1185918903@qq.com
@license: Apache Licence
@time: 2024/6/5 22:37

"""
import pandas as pd
from transformers import AutoTokenizer, AutoModel
import torch
import torch.nn.functional as F
import faiss
import numpy as np
import os
from tqdm import tqdm
os.environ["KMP_DUPLICATE_LIB_OK"]="TRUE"
class SemanticEmbedding:

    def __init__(self, model_name='sentence-transformers/all-mpnet-base-v2'):
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModel.from_pretrained(model_name)

    # Mean Pooling - Take attention mask into account for correct averaging
    def mean_pooling(self, model_output, attention_mask):
        token_embeddings = model_output[0]  # First element of model_output contains all token embeddings
        input_mask_expanded = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
        return torch.sum(token_embeddings * input_mask_expanded, 1) / torch.clamp(input_mask_expanded.sum(1), min=1e-9)

    def get_embedding(self, sentences):
        # Tokenize sentences
        encoded_input = self.tokenizer(sentences, padding=True, truncation=True, return_tensors='pt')
        with torch.no_grad():
            model_output = self.model(**encoded_input)
        # Perform pooling
        sentence_embeddings = self.mean_pooling(model_output, encoded_input['attention_mask'])

        # Normalize embeddings
        sentence_embeddings = F.normalize(sentence_embeddings, p=2, dim=1)
        return sentence_embeddings.detach().numpy()
class FaissIdx:

    def __init__(self, model, dim=768):
        self.index = faiss.IndexFlatIP(dim)
        # Maintaining the document data
        self.doc_map = dict()
        self.model = model
        self.ctr = 0

    def add_doc(self, document_text):
        self.index.add(self.model.get_embedding(document_text))
        self.doc_map[self.ctr] = document_text # store the original document text
        self.ctr += 1

    def search_doc(self, query, k=3):
        D, I = self.index.search(self.model.get_embedding(query), k)
        return [{self.doc_map[idx]: score} for idx, score in zip(I[0], D[0]) if idx in self.doc_map]
if __name__ == '__main__':
    model = SemanticEmbedding(r'I:\pretrained_models\bert\english\paraphrase-multilingual-mpnet-base-v2')
    a = model.get_embedding("我喜欢打篮球")
    print(a)
    print(a.shape)

    index = FaissIdx(model)
    index.add_doc("笔记本电脑")
    index.add_doc("医生的办公室")
    result=index.search_doc("个人电脑")
    print(result)


    # 加载测试文档
    data=pd.read_json('../../data/zh_refine.json', lines=True)[:50]
    print(data)
    print(data.columns)

    for documents in tqdm(data['positive'],total=len(data)):
        for document in documents:
            index.add_doc(document)

    for documents in tqdm(data['negative'],total=len(data)):
        for document in documents:
            index.add_doc(document)

    result=index.search_doc("2022年特斯拉交付量")
    print(result)
