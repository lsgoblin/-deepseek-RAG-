"""Minimal Streamlit demo for the RAG project."""

from __future__ import annotations

from pathlib import Path

try:
    import streamlit as st
except ModuleNotFoundError as exc:  # pragma: no cover - depends on runtime env
    raise RuntimeError("Missing dependency `streamlit`. Install requirements first.") from exc

try:
    from src.config import get_settings
    from src.loaders import discover_documents
    from src.rag_pipeline import answer_question, ensure_knowledge_base
    from src.schemas import RetrievedChunk
    from src.vectordb import load_vector_store
except ModuleNotFoundError:  # pragma: no cover - script execution fallback
    from config import get_settings
    from loaders import discover_documents
    from rag_pipeline import answer_question, ensure_knowledge_base
    from schemas import RetrievedChunk
    from vectordb import load_vector_store


PAGE_TITLE = "DeepSeek RAG Demo"
PAGE_ICON = "📘"


def _relative_path(path: Path, root: Path) -> str:
    """Render a path relative to the project root when possible."""

    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def get_app_status() -> dict[str, object]:
    """Collect lightweight runtime status for sidebar display."""

    settings = get_settings()
    discovered_docs = discover_documents(
        data_dir=settings.data_dir,
        max_docs=settings.max_docs,
    )

    status: dict[str, object] = {
        "settings": settings,
        "discovered_docs": discovered_docs,
        "doc_count": len(discovered_docs),
        "has_api_key": bool(settings.deepseek_api_key),
        "vector_count": 0,
        "vector_error": None,
    }

    try:
        store = load_vector_store(settings.vector_db_type, settings.vector_db_dir)
        if hasattr(store, "count"):
            status["vector_count"] = int(store.count())
    except Exception as exc:  # pragma: no cover - runtime environment dependent
        status["vector_error"] = str(exc)

    return status


def render_sidebar() -> None:
    """Render settings and knowledge-base status."""

    status = get_app_status()
    settings = status["settings"]
    discovered_docs = status["discovered_docs"]

    st.sidebar.header("系统状态")
    st.sidebar.write(
        f"数据目录：`{_relative_path(settings.data_dir, settings.project_root)}`"
    )
    st.sidebar.write(
        f"向量库目录：`{_relative_path(settings.vector_db_dir, settings.project_root)}`"
    )
    st.sidebar.write(f"Embedding：`{settings.embedding_model}`")
    st.sidebar.write(f"LLM：`{settings.deepseek_model}`")
    st.sidebar.write(f"Top-K：`{settings.top_k}`")
    st.sidebar.write(
        f"Chunk：`{settings.chunk_size}` / Overlap：`{settings.chunk_overlap}`"
    )

    if status["has_api_key"]:
        st.sidebar.success("已检测到 DeepSeek API Key")
    else:
        st.sidebar.warning(
            "未检测到 DeepSeek API Key，当前只能查看知识库状态，无法生成答案。"
        )

    vector_error = status["vector_error"]
    if vector_error:
        st.sidebar.error(f"向量库状态读取失败：{vector_error}")
    else:
        st.sidebar.write(f"当前索引片段数：`{status['vector_count']}`")

    if st.sidebar.button("构建 / 刷新知识库", use_container_width=True):
        with st.spinner("正在构建知识库..."):
            try:
                store = ensure_knowledge_base()
                count = int(store.count()) if hasattr(store, "count") else 0
            except Exception as exc:  # pragma: no cover - runtime environment dependent
                st.sidebar.error(f"知识库构建失败：{exc}")
            else:
                st.sidebar.success(f"知识库已就绪，当前片段数：{count}")

    st.sidebar.divider()
    st.sidebar.subheader("已发现文档")
    if not discovered_docs:
        st.sidebar.info("`data/` 目录下还没有可用文档。")
        return

    for file_path in discovered_docs[:8]:
        st.sidebar.caption(_relative_path(file_path, settings.project_root))

    if len(discovered_docs) > 8:
        st.sidebar.caption(f"... 还有 {len(discovered_docs) - 8} 个文档")


def render_answer_sources(sources: list[str]) -> None:
    """Render the normalized source list."""

    st.subheader("来源")
    if not sources:
        st.info("当前回答没有返回来源列表。")
        return

    for source in sources:
        st.markdown(f"- `{source}`")


def render_retrieved_chunks(retrieved_chunks: list[RetrievedChunk]) -> None:
    """Render retrieval hits as expandable evidence cards."""

    st.subheader("检索片段")
    if not retrieved_chunks:
        st.info("本次提问没有检索到相关片段。")
        return

    for index, item in enumerate(retrieved_chunks, start=1):
        score_text = "unknown"
        if item.score is not None:
            score_text = f"{item.score:.4f}"

        label = f"片段 {index} | {item.chunk.source_doc} | 相似度 {score_text}"
        with st.expander(label, expanded=index == 1):
            st.caption(f"chunk_id: {item.chunk.chunk_id}")
            st.caption(f"chunk_index: {item.chunk.chunk_index}")
            st.write(item.chunk.chunk_text)


def render_main() -> None:
    """Render the main question-answer workflow."""

    st.title(PAGE_TITLE)
    st.caption("课程项目演示页：输入问题后，查看答案、来源和检索证据。")

    default_question = st.session_state.get(
        "question_input",
        "这些文档主要在讲什么？",
    )
    question = st.text_area(
        "输入问题",
        value=default_question,
        height=120,
        placeholder="例如：这些资料中有哪些适合即梦或 Midjourney 的提示词写法？",
    )
    st.session_state["question_input"] = question

    if not st.button("开始提问", type="primary", use_container_width=True):
        st.info("输入一个问题后点击“开始提问”。")
        return

    if not question.strip():
        st.error("问题不能为空。")
        return

    with st.spinner("正在检索并生成答案..."):
        try:
            answer, retrieved_chunks = answer_question(question)
        except Exception as exc:  # pragma: no cover - runtime environment dependent
            st.error(f"运行失败：{exc}")
            return

    st.subheader("最终答案")
    st.write(answer.answer_text)

    render_answer_sources(answer.sources)
    render_retrieved_chunks(retrieved_chunks)


def main() -> None:
    """Run the Streamlit demo app."""

    st.set_page_config(
        page_title=PAGE_TITLE,
        page_icon=PAGE_ICON,
        layout="wide",
    )
    render_sidebar()
    render_main()


if __name__ == "__main__":
    main()
