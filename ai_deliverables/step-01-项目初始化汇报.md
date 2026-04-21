# Step 01 项目初始化汇报

## 本步目标

根据《项目计划》先完成项目初始化和目录结构搭建，不编写业务代码。

## 实际完成内容

1. 阅读并整理了项目计划说明。
2. 创建了基础目录结构：
   - `data/`
   - `vector_store/`
   - `src/`
   - `notebooks/`
   - `outputs/screenshots/`
   - `outputs/experiment_results/`
3. 创建了基础配置与说明文件：
   - `requirements.txt`
   - `.env.example`
   - `.gitignore`
   - `README.md`
4. 创建了源码占位模块，暂不写业务实现：
   - `build_kb.py`
   - `config.py`
   - `loaders.py`
   - `splitter.py`
   - `embedder.py`
   - `vectordb.py`
   - `retriever.py`
   - `prompt_builder.py`
   - `llm.py`
   - `rag_pipeline.py`
   - `compare.py`
   - `ui.py`

## 产出文件

- `D:\test\deployment-model-v2\README.md`
- `D:\test\deployment-model-v2\requirements.txt`
- `D:\test\deployment-model-v2\.env.example`
- `D:\test\deployment-model-v2\.gitignore`
- `D:\test\deployment-model-v2\src\*.py`
- `D:\test\deployment-model-v2\ai_deliverables\README.md`

## 当前未完成项

- 未创建虚拟环境
- 未安装依赖
- 未实现任何业务逻辑
- 未接入 DeepSeek API
- 未建立可运行的知识库流程

## 在未部署环境前可以继续做的工作

在还没有部署环境、没有安装依赖的情况下，仍然可以推进以下工作：

1. 完善项目目录与模块边界设计。
2. 编写 `config.py` 的配置结构和参数约定。
3. 设计各模块接口、函数签名、数据结构和 docstring。
4. 补充 `README.md` 的开发说明、运行流程和交付说明。
5. 编写示例数据目录规范和输出目录规范。
6. 搭建 CLI 交互流程草图，但先不接真实模型。
7. 设计 RAG 主流程、对比实验流程和调用顺序。
8. 编写占位测试文件与测试计划。
9. 规划异常处理、日志、配置加载和路径管理方案。
10. 整理课程作业所需的截图、实验结果、报告目录规范。

## 暂时不适合做的工作

以下工作通常需要环境或依赖就绪后再进行：

1. 安装第三方依赖并验证兼容性。
2. 解析 PDF / DOCX 并做真实文档读取测试。
3. 加载 embedding 模型并生成向量。
4. 创建和验证 Chroma / FAISS 向量库。
5. 调用 DeepSeek API 做联调。
6. 运行 CLI / Web 交互并做端到端测试。

## 下一步建议

优先继续做“无环境也能推进”的部分：

1. 先实现 `src/config.py` 的配置骨架。
2. 再定义文档加载、切分、检索等模块的输入输出接口。
3. 最后再进入环境部署、依赖安装和真实联调。

