import json
import logging
import uuid
from collections.abc import Awaitable, Callable
from typing import Any

from app.models.intelligence import (
    AgentStep,
    EvidenceItem,
    IntelligenceQueryResponse,
    SourceReference,
)
from app.services.intelligence.ollama_client import OllamaClient, OllamaError
from app.services.intelligence.tools import execute_tool, get_tool_specs

logger = logging.getLogger("app.intelligence.agent")

SYSTEM_PROMPT = """You are a PYQ (Previous Year Questions) exam-intelligence assistant.

You have tools to retrieve real exam data: semantic question search, Question DNA lookup, \
question relationships/families, exam trends and important topics, and question source lookup.

Rules you MUST follow:
1. Only state exam facts -- question text, counts, years, topics, difficulty, scores, any \
statistic -- that were returned by a tool call earlier in this conversation. Never invent or \
guess a number, year, question count, or question text that did not come from a tool result.
2. If the retrieved evidence does not answer the question, say so explicitly instead of guessing.
3. Call at least one tool before answering any question about exam content.
4. Your final answer should explain/synthesize what the tools found, in plain language -- do \
not just restate raw JSON.
"""

ChatFn = Callable[[list[dict[str, Any]], list[dict[str, Any]]], Awaitable[dict[str, Any]]]
ExecuteToolFn = Callable[[str, dict[str, Any]], Awaitable[dict[str, Any]]]

DEFAULT_MAX_ITERATIONS = 5

NO_EVIDENCE_ANSWER = (
    "I don't have enough retrieved evidence from the PYQ database to answer this confidently. "
    "Try rephrasing, or ask about a specific topic, subject, or question."
)
OLLAMA_UNAVAILABLE_ANSWER = (
    "I couldn't reach the local Ollama service, so I can't generate a grounded answer right "
    "now. Please make sure Ollama is running and try again."
)
OLLAMA_FAILED_MID_CONVERSATION_ANSWER = (
    "I retrieved evidence from the PYQ database (see below), but the local Ollama service "
    "failed before I could finish composing an answer from it. Please try again -- the "
    "retrieved evidence is still shown below in case it's useful."
)
STEP_LIMIT_ANSWER = (
    "I gathered some evidence but couldn't finish forming an answer within the step limit. "
    "See the retrieved evidence and sources below."
)


async def _default_chat_fn(messages: list[dict[str, Any]], tools: list[dict[str, Any]]) -> dict[str, Any]:
    client = OllamaClient()
    return await client.chat(messages, tools=tools)


def _dedupe_sources(sources: list[SourceReference]) -> list[SourceReference]:
    seen: set[str] = set()
    deduped: list[SourceReference] = []
    for source in sources:
        if source.question_id in seen:
            continue
        seen.add(source.question_id)
        deduped.append(source)
    return deduped


def _source_from_dict(question_id: str | None, source: dict[str, Any] | None) -> SourceReference | None:
    if not question_id or not source:
        return None
    return SourceReference(
        question_id=question_id,
        file=source.get("file", ""),
        page=source.get("page", 0),
        question_number=source.get("question_number", 0),
        section=source.get("section"),
    )


def collect_evidence_and_sources(
    tool_name: str, result: dict[str, Any]
) -> tuple[list[EvidenceItem], list[SourceReference]]:
    """Turns one tool's raw result into structured, tool-sourced
    evidence/source citations. This is the only place that decides
    what counts as "retrieved fact" -- the LLM never touches this.
    """
    evidence: list[EvidenceItem] = []
    sources: list[SourceReference] = []

    if "error" in result:
        return evidence, sources

    if tool_name == "semantic_pyq_search":
        for item in result.get("results", []):
            evidence.append(
                EvidenceItem(
                    type="question",
                    question_id=item.get("question_id"),
                    summary=f"Similarity {item.get('similarity')}: {item.get('text', '')[:160]}",
                    data=item,
                )
            )
            source = _source_from_dict(item.get("question_id"), item.get("source"))
            if source:
                sources.append(source)

    elif tool_name == "question_dna_lookup":
        if "classification" in result:
            evidence.append(
                EvidenceItem(
                    type="question_dna",
                    question_id=result.get("question_id"),
                    summary=f"Question DNA for {result.get('question_id')}",
                    data=result,
                )
            )
        for match in result.get("matches", []):
            dna = match.get("classification", {})
            evidence.append(
                EvidenceItem(
                    type="question_dna",
                    question_id=match.get("question_id"),
                    summary=f"{dna.get('subject')} / {dna.get('topic')}",
                    data=match,
                )
            )

    elif tool_name == "question_relationships_lookup":
        for relationship in result.get("related", []):
            evidence.append(
                EvidenceItem(
                    type="relationship",
                    question_id=relationship.get("question_id"),
                    summary=f"{relationship.get('type')} ({relationship.get('confidence')}): "
                    f"{relationship.get('reason')}",
                    data=relationship,
                )
            )

    elif tool_name == "exam_trends_lookup":
        evidence.append(
            EvidenceItem(
                type="exam_trends",
                question_id=None,
                summary=f"Exam {result.get('mode', 'trends')} data retrieved.",
                data=result,
            )
        )

    elif tool_name == "question_source_lookup":
        if result.get("question_id"):
            evidence.append(
                EvidenceItem(
                    type="source",
                    question_id=result.get("question_id"),
                    summary=f"Source: {result.get('source', {}).get('file')} "
                    f"p.{result.get('source', {}).get('page')}",
                    data=result,
                )
            )
            source = _source_from_dict(result.get("question_id"), result.get("source"))
            if source:
                sources.append(source)

    return evidence, sources


def _parse_arguments(raw: Any) -> dict[str, Any]:
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            logger.warning("Could not parse tool arguments as JSON: %r", raw)
    return {}


async def run_agent(
    query: str,
    chat_fn: ChatFn | None = None,
    execute_tool_fn: ExecuteToolFn | None = None,
    max_iterations: int = DEFAULT_MAX_ITERATIONS,
) -> IntelligenceQueryResponse:
    """Runs the agentic RAG loop: the model decides which tools to call,
    we execute them and feed results back, repeating until it produces
    a final answer with no further tool calls (or the step limit is
    hit). `chat_fn`/`execute_tool_fn` are injectable so this can be
    tested without a live Ollama server or database.
    """
    chat_fn = chat_fn or _default_chat_fn
    execute_tool_fn = execute_tool_fn or execute_tool
    tool_specs = get_tool_specs()

    messages: list[dict[str, Any]] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": query},
    ]

    steps: list[AgentStep] = []
    evidence: list[EvidenceItem] = []
    sources: list[SourceReference] = []
    tool_calls_made = 0

    for iteration in range(max_iterations):
        try:
            response = await chat_fn(messages, tool_specs)
        except OllamaError as exc:
            logger.error("Ollama call failed on iteration %s: %s", iteration, exc)
            steps.append(AgentStep(step=len(steps) + 1, type="error", result_summary=str(exc)))
            # Distinguish "never reached Ollama at all" from "failed partway
            # through, after evidence was already retrieved" -- the response
            # should never bury evidence that was genuinely gathered.
            answer = (
                OLLAMA_FAILED_MID_CONVERSATION_ANSWER if tool_calls_made > 0 else OLLAMA_UNAVAILABLE_ANSWER
            )
            return IntelligenceQueryResponse(
                answer=answer,
                evidence=evidence,
                sources=_dedupe_sources(sources),
                steps=steps,
                tool_calls_made=tool_calls_made,
                grounded=False,
                error=str(exc),
            )

        message = response.get("message", {}) or {}
        tool_calls = message.get("tool_calls") or []

        if not tool_calls:
            final_text = (message.get("content") or "").strip()

            if tool_calls_made == 0:
                logger.warning("Agent tried to answer with no tool calls; using safe fallback.")
                return IntelligenceQueryResponse(
                    answer=NO_EVIDENCE_ANSWER,
                    evidence=evidence,
                    sources=_dedupe_sources(sources),
                    steps=steps,
                    tool_calls_made=tool_calls_made,
                    grounded=False,
                )

            steps.append(
                AgentStep(step=len(steps) + 1, type="final_answer", result_summary=final_text[:200])
            )
            logger.info("Agent produced a final answer after %s tool call(s).", tool_calls_made)
            return IntelligenceQueryResponse(
                answer=final_text,
                evidence=evidence,
                sources=_dedupe_sources(sources),
                steps=steps,
                tool_calls_made=tool_calls_made,
                grounded=True,
            )

        messages.append(message)

        for call in tool_calls:
            function = call.get("function", {}) or {}
            tool_name = function.get("name", "")
            arguments = _parse_arguments(function.get("arguments"))
            tool_call_id = call.get("id") or str(uuid.uuid4())

            logger.info("Agent calling tool '%s' with args %s", tool_name, arguments)
            result = await execute_tool_fn(tool_name, arguments)

            tool_calls_made += 1
            steps.append(
                AgentStep(
                    step=len(steps) + 1,
                    type="tool_call",
                    tool=tool_name,
                    arguments=arguments,
                    result_summary=json.dumps(result, default=str)[:300],
                )
            )
            logger.info("Tool '%s' completed (step %s)", tool_name, len(steps))

            item_evidence, item_sources = collect_evidence_and_sources(tool_name, result)
            evidence.extend(item_evidence)
            sources.extend(item_sources)

            messages.append(
                {
                    "role": "tool",
                    "content": json.dumps(result, default=str),
                    "tool_call_id": tool_call_id,
                }
            )

    logger.warning("Agent exceeded max_iterations=%s without a final answer.", max_iterations)
    return IntelligenceQueryResponse(
        answer=STEP_LIMIT_ANSWER,
        evidence=evidence,
        sources=_dedupe_sources(sources),
        steps=steps,
        tool_calls_made=tool_calls_made,
        grounded=tool_calls_made > 0,
    )
