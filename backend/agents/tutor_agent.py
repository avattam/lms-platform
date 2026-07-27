"""LangChain AI Tutor Agent with Granular SSE Event Streaming."""
import json
import logging
from collections.abc import AsyncGenerator

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from sqlalchemy.ext.asyncio import AsyncSession
from core.config import settings
from agents.tools import create_lms_tools
from services.search_service import hybrid_search

logger = logging.getLogger(__name__)


def _get_llm():
    """Get configured LangChain Chat Model (ChatOpenAI or ChatOllama)."""
    provider = (settings.AI_PROVIDER or "openai").lower()

    if provider == "openai":
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=settings.OPENAI_LLM_MODEL or "gpt-4o-mini",
            api_key=settings.OPENAI_API_KEY or "sk-placeholder",
            base_url=settings.OPENAI_BASE_URL or "https://api.openai.com/v1",
            temperature=0.7,
            streaming=True,
        )
    else:
        from langchain_ollama import ChatOllama

        return ChatOllama(
            model=settings.LLM_MODEL or "qwen3:4b",
            base_url=settings.OLLAMA_BASE_URL or "http://localhost:11434",
            temperature=0.7,
        )


async def stream_tutor_agent(
    session_id: str,
    user_id: str,
    user_message: str,
    history_messages: list[dict],
    db: AsyncSession,
) -> AsyncGenerator[str, None]:
    """
    Executes the LangChain AI Tutor Agent and yields structured SSE JSON events:
    - {"type": "thought", "status": "..."}
    - {"type": "sources", "sources": [...]}
    - {"type": "token", "token": "..."}
    - {"type": "done"}
    """
    tools = create_lms_tools(db=db, current_user_id=user_id)
    tools_by_name = {t.name: t for t in tools}

    llm = _get_llm()
    try:
        llm_with_tools = llm.bind_tools(tools)
    except Exception as e:
        logger.warning(f"Could not bind tools directly to LLM ({e}), falling back to direct LLM execution.")
        llm_with_tools = llm

    # Build conversation memory
    system_prompt = (
        "You are an expert AI Tutor for an online Learning Management System (LMS).\n"
        "You are helpful, encouraging, and clear.\n"
        "When answering questions about course topics, always search the knowledge base first using search_knowledge_base.\n"
        "If you use retrieved context, integrate it smoothly and concisely into your answer."
    )

    messages = [SystemMessage(content=system_prompt)]
    for m in history_messages:
        role = m.get("role", "human")
        content = m.get("content", "")
        if role in ("human", "user"):
            messages.append(HumanMessage(content=content))
        elif role in ("ai", "assistant"):
            messages.append(AIMessage(content=content))

    messages.append(HumanMessage(content=user_message))

    # --- Step 1: Execute Tool Decision Pass ---
    yield f"data: {json.dumps({'type': 'thought', 'status': '🧠 Reasoning about your question...'})}\n\n"

    try:
        first_response = await llm_with_tools.ainvoke(messages)
    except Exception as e:
        logger.error(f"LLM tool invocation error: {e}")
        first_response = AIMessage(content="")

    tool_calls = getattr(first_response, "tool_calls", []) or []

    # Fallback: if model didn't invoke tool but user asked about course material, run hybrid search automatically
    if not tool_calls:
        yield f"data: {json.dumps({'type': 'thought', 'status': '🔍 Searching course knowledge base...'})}\n\n"
        search_results = await hybrid_search(query=user_message, db=db, top_k=5)
        if search_results:
            sources_meta = []
            formatted_chunks = []
            for i, r in enumerate(search_results, 1):
                meta = r.get("metadata") or {}
                source_title = meta.get("filename") or meta.get("source") or meta.get("source_url") or f"Document #{i}"
                sources_meta.append({
                    "id": str(r.get("id")),
                    "title": source_title,
                    "snippet": r.get("text", "")[:180] + "...",
                    "score": round(r.get("score", 0), 3),
                })
                formatted_chunks.append(f"[Source {i}: {source_title}]\n{r.get('text')}")

            yield f"data: {json.dumps({'type': 'sources', 'sources': sources_meta})}\n\n"

            context_block = "\n\n".join(formatted_chunks)
            messages.append(
                SystemMessage(
                    content=f"Retrieved Course Context:\n{context_block}\n\nUse this context to answer the student's question accurately."
                )
            )

    else:
        # Agent decided to invoke tool(s)
        messages.append(first_response)
        for tc in tool_calls:
            t_name = tc.get("name")
            t_args = tc.get("args") or {}
            t_id = tc.get("id", "tool_1")

            status_msg = f"🔍 Running tool '{t_name}'..."
            if t_name == "search_knowledge_base":
                status_msg = f"🔍 Searching knowledge base for '{t_args.get('query', user_message)}'..."
            elif t_name == "query_course_catalog":
                status_msg = "📚 Querying LMS course catalog..."
            elif t_name == "get_user_learning_progress":
                status_msg = "📊 Fetching your learning progress..."

            yield f"data: {json.dumps({'type': 'thought', 'status': status_msg})}\n\n"

            target_tool = tools_by_name.get(t_name)
            if target_tool:
                try:
                    tool_output = await target_tool.ainvoke(t_args)
                except Exception as ex:
                    tool_output = f"Tool execution failed: {ex}"
            else:
                tool_output = f"Tool '{t_name}' not found."

            # If search_knowledge_base was called, attempt to parse sources to send to UI
            if t_name == "search_knowledge_base":
                search_results = await hybrid_search(query=t_args.get("query", user_message), db=db, top_k=5)
                if search_results:
                    sources_meta = []
                    for i, r in enumerate(search_results, 1):
                        meta = r.get("metadata") or {}
                        source_title = meta.get("filename") or meta.get("source") or meta.get("source_url") or f"Document #{i}"
                        sources_meta.append({
                            "id": str(r.get("id")),
                            "title": source_title,
                            "snippet": r.get("text", "")[:180] + "...",
                            "score": round(r.get("score", 0), 3),
                        })
                    yield f"data: {json.dumps({'type': 'sources', 'sources': sources_meta})}\n\n"

            messages.append(ToolMessage(content=str(tool_output), tool_call_id=t_id))

    # --- Step 2: Final Response Stream Pass ---
    yield f"data: {json.dumps({'type': 'thought', 'status': '✍️ Synthesizing response...'})}\n\n"

    try:
        async for chunk in llm.astream(messages):
            token = chunk.content if isinstance(chunk.content, str) else ""
            if token:
                yield f"data: {json.dumps({'type': 'token', 'token': token})}\n\n"
    except Exception as e:
        logger.error(f"Error in LLM stream: {e}")
        yield f"data: {json.dumps({'type': 'token', 'token': ' An error occurred while generating response.'})}\n\n"

    yield "data: {\"type\": \"done\"}\n\n"
