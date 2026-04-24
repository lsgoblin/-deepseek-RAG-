# deployment-model-v2

基于 DeepSeek 的 RAG 信息检索系统 + 面向 AI 生成图片提示词优化的应用场景
底层：用 DeepSeek + RAG 做信息检索与知识增强
上层：做一个帮助用户优化 AI 生图提示词的网站
## 当前状态

## 目录结构

```text
deployment-model-v2/
├─ data/
├─ notebooks/
├─ outputs/
│  ├─ experiment_results/
│  └─ screenshots/
├─ src/
│  ├─ __init__.py
│  ├─ build_kb.py
│  ├─ compare.py
│  ├─ config.py
│  ├─ embedder.py
│  ├─ llm.py
│  ├─ loaders.py
│  ├─ prompt_builder.py
│  ├─ rag_pipeline.py
│  ├─ retriever.py
│  ├─ splitter.py
│  ├─ ui.py
│  └─ vectordb.py
├─ vector_store/
├─ .env.example
├─ .gitignore
├─ README.md
├─ requirements.txt
└─ 项目计划.md
```


