# deployment-model-v2

基于 DeepSeek + RAG 的 AI 生图提示词优化课程项目。

本项目将课程要求中的 RAG 主链路落地到一个具体应用场景：用户输入原始生图提示词，系统先从本地知识库中检索提示词参考，再结合 DeepSeek 生成更完整、更可控、可追溯的优化结果。

## 1. 项目简介

项目目标：

- 支持本地知识库构建
- 支持向量检索与 RAG 生成
- 支持 AI 生图提示词优化
- 支持 CLI、Web API 与实验对比
- 支持课程报告所需的实验结果输出

应用场景：

- 人物类提示词优化
- 场景类提示词优化
- 产品海报类提示词优化

## 2. 功能说明

- 加载 `md / pdf / docx / xlsx` 文档并构建知识库
- 使用 `sentence-transformers` 生成向量
- 使用 `Chroma` 持久化向量库
- 提供标准 RAG 问答主流程
- 提供提示词优化接口 `/api/optimize`
- 提供知识库状态接口 `/api/status`
- 提供知识库重建接口 `/api/rebuild-kb`
- 提供最小可用 CLI
- 提供 `LLM-only / Retrieval-only / RAG` 三模式对比实验

## 3. 技术栈

- Python 3.10+
- DeepSeek Chat Completions API
- sentence-transformers
- ChromaDB
- FastAPI
- Streamlit
- openpyxl
- pypdf
- python-docx

## 4. 目录结构

```text
deployment-model-v2/
├─ ai_deliverables/              # 过程文档与课程交付材料
├─ data/                         # 知识库数据
│  ├─ raw/                       # 原始数据
│  └─ final/                     # 整理后的知识库文档
├─ outputs/
│  ├─ experiment_results/        # 实验结果输出
│  └─ screenshots/               # 截图输出
├─ reports/                      # 最终实验报告
├─ src/
│  ├─ api_app.py                 # FastAPI 后端
│  ├─ build_kb.py                # 文档加载与切分摘要
│  ├─ build_vector_store.py      # 向量库构建入口
│  ├─ compare.py                 # 三模式对比实验
│  ├─ config.py                  # 配置管理
│  ├─ embedder.py                # 向量化
│  ├─ llm.py                     # DeepSeek 调用
│  ├─ loaders.py                 # 文档加载
│  ├─ prompt_builder.py          # RAG Prompt 构造
│  ├─ prompt_optimizer.py        # 提示词优化主逻辑
│  ├─ rag_pipeline.py            # RAG 主流程
│  ├─ retriever.py               # 检索模块
│  ├─ ui.py                      # CLI
│  ├─ vectordb.py                # 向量库操作
│  ├─ web_app.py                 # Streamlit 演示页
│  └─ deepseek_rag_homepage_prototype.html
├─ vector_store/                 # Chroma 持久化目录
├─ .env.example
├─ README.md
└─ requirements.txt
```

## 5. 安装步骤

建议在项目根目录 `D:\test\deployment-model-v2` 下执行：

```powershell
pip install -r requirements.txt
Copy-Item .env.example .env
```

然后编辑 `.env`，至少填写：

```env
DEEPSEEK_API_KEY=your_deepseek_api_key_here
```

## 6. 环境变量说明

必填项：

- `DEEPSEEK_API_KEY`：DeepSeek API Key

常用配置：

- `DEEPSEEK_BASE_URL`：默认 `https://api.deepseek.com`
- `DEEPSEEK_MODEL`：默认 `deepseek-chat`
- `EMBEDDING_MODEL`：默认 `BAAI/bge-small-zh`
- `VECTOR_DB_TYPE`：默认 `chroma`
- `VECTOR_DB_DIR`：默认 `./vector_store`
- `TOP_K`：默认 `3`
- `CHUNK_SIZE`：默认 `400`
- `CHUNK_OVERLAP`：默认 `80`
- `TEMPERATURE`：默认 `0.2`
- `MAX_DOCS`：默认 `200`

## 7. 数据准备

- 将知识库文档放入 `data/`
- 当前仓库已包含课程实验所需的基础提示词资料
- `data/raw/` 下保留原始 Excel 数据
- `data/final/` 下保留整理后的 Markdown 知识库

首次运行建议先构建向量库：

```powershell
python src/build_vector_store.py
```

## 8. 运行方式

### 8.1 运行 Web API

推荐命令：

```powershell
uvicorn src.api_app:app --host 127.0.0.1 --port 8010
```

如果 `8000` 端口未被占用，也可以使用：

```powershell
uvicorn src.api_app:app --reload
```

启动后打开：

- 首页：`http://127.0.0.1:8010/`
- 状态接口：`http://127.0.0.1:8010/api/status`

说明：

- 页面原型文件为 `src/deepseek_rag_homepage_prototype.html`
- 页面中的按钮依赖后端接口，因此不建议直接双击 HTML 文件打开

### 8.2 运行 CLI

交互式模式：

```powershell
python src/ui.py
```

单次优化：

```powershell
python src/ui.py --prompt "一款高端香水的广告海报" --platform 通用 --style "商业摄影，极简高级" --goal "突出材质、品牌感和广告构图"
```

三模式对比：

```powershell
python src/ui.py --mode compare --prompt "一款高端香水的广告海报" --platform 通用 --style "商业摄影，极简高级" --goal "突出材质、品牌感和广告构图"
```

### 8.3 运行 Streamlit

```powershell
streamlit run src/web_app.py
```

说明：

- Streamlit 页可作为备用演示入口
- 当前课程主展示建议优先使用 FastAPI 首页原型

## 9. 对比实验

生成内置三组实验结果：

```powershell
python src/compare.py --sample-suite --json-out ai_deliverables/step-16-对比实验结果.json --markdown-out ai_deliverables/step-16-对比实验结果.md
```

三种模式说明：

- `LLM-only`：仅调用大模型，不提供检索上下文
- `Retrieval-only`：仅展示检索到的知识片段，不生成最终提示词
- `RAG`：检索后再生成最终优化提示词

## 10. 推荐演示顺序

最稳妥的本地演示流程如下：

1. `pip install -r requirements.txt`
2. 配置 `.env`
3. `python src/build_vector_store.py`
4. `uvicorn src.api_app:app --host 127.0.0.1 --port 8010`
5. 打开 `http://127.0.0.1:8010/`
6. 输入一条示例提示词进行优化
7. 查看优化结果、来源文档和检索片段

## 11. 常见问题

### 11.1 没有 `.env` 能运行吗

可以完成：

- 知识库扫描
- 向量库构建
- Retrieval-only 对比实验

不能完成：

- `LLM-only`
- `RAG`
- `/api/optimize`

### 11.2 首次运行为什么较慢

- 首次会加载 embedding 模型
- 首次会初始化 Chroma 向量库

### 11.3 为什么 `uvicorn` 无法启动

常见原因：

- 端口被占用
- Windows 本地权限或安全软件拦截

建议直接换端口：

```powershell
uvicorn src.api_app:app --host 127.0.0.1 --port 8010
```

### 11.4 为什么页面状态正常但优化失败

一般原因：

- API Key 缺失
- DeepSeek 请求失败
- 模型返回格式不符合预期

### 11.5 为什么检索不到内容

- 检查 `data/` 下是否存在有效文档
- 重新执行：

```powershell
python src/build_vector_store.py
```

## 12. 交付材料位置

- 过程材料：`ai_deliverables/`
- 实验结果：`outputs/experiment_results/`
- 截图：`outputs/screenshots/`
- 最终实验报告：`reports/`

## 13. 当前结论

该项目已经具备课程项目所需的核心代码闭环：

- 知识库构建
- 向量检索
- DeepSeek 生成
- Prompt 优化
- 三模式对比实验
- CLI 与 Web 交互入口

如果需要课程最终提交，还应补齐：

- 最终报告 PDF
- 最终打包提交材料
