import pytest

from app.services.intelligence.agent import run_agent
from app.services.intelligence.ollama_client import OllamaError


def _assistant_message(content: str = "", tool_calls: list[dict] | None = None) -> dict:
    message = {"role": "assistant", "content": content}
    if tool_calls:
        message["tool_calls"] = tool_calls
    return {"message": message}


def _tool_call(call_id: str, name: str, arguments: dict) -> dict:
    return {"id": call_id, "function": {"name": name, "arguments": arguments}}


@pytest.mark.asyncio
async def test_multi_step_query_calls_tool_then_answers():
    """The core agentic-RAG path: model asks for a tool, gets results,
    then answers using them -- without ever being told the answer
    directly by the test."""
    call_log = []

    async def fake_chat(messages, tools):
        call_log.append(len(messages))
        if len(call_log) == 1:
            return _assistant_message(
                tool_calls=[_tool_call("c1", "semantic_pyq_search", {"query": "pulley"})]
            )
        return _assistant_message(content="Pulley questions mostly cover tension and acceleration.")

    async def fake_execute_tool(name, arguments):
        assert name == "semantic_pyq_search"
        assert arguments == {"query": "pulley"}
        return {
            "results": [
                {
                    "question_id": "q1",
                    "similarity": 0.92,
                    "text": "Two blocks connected by a string over a pulley...",
                    "subject": "Physics",
                    "topic": "Mechanics",
                    "source": {"file": "2021.pdf", "page": 1, "question_number": 18, "section": None},
                }
            ]
        }

    result = await run_agent("Find pulley questions", chat_fn=fake_chat, execute_tool_fn=fake_execute_tool)

    assert result.grounded is True
    assert result.tool_calls_made == 1
    assert "tension" in result.answer or "acceleration" in result.answer
    assert len(result.evidence) == 1
    assert result.evidence[0].question_id == "q1"
    assert len(result.sources) == 1
    assert result.sources[0].file == "2021.pdf"
    # Two steps recorded: one tool call, one final answer.
    assert [s.type for s in result.steps] == ["tool_call", "final_answer"]


@pytest.mark.asyncio
async def test_agent_performs_second_retrieval_when_first_is_insufficient():
    """A genuinely multi-step query: the model calls one tool, decides
    it needs more evidence, calls a second tool, then answers."""
    responses = [
        _assistant_message(
            tool_calls=[_tool_call("c1", "question_dna_lookup", {"question_id": "q1"})]
        ),
        _assistant_message(
            tool_calls=[_tool_call("c2", "question_relationships_lookup", {"question_id": "q1"})]
        ),
        _assistant_message(content="q1 is a Mechanics question with two near-duplicate variants."),
    ]
    call_index = {"n": 0}

    async def fake_chat(messages, tools):
        response = responses[call_index["n"]]
        call_index["n"] += 1
        return response

    tool_results = {
        "question_dna_lookup": {
            "question_id": "q1",
            "text": "A block on a pulley...",
            "classification": {"subject": "Physics", "topic": "Mechanics"},
        },
        "question_relationships_lookup": {
            "question_id": "q1",
            "question_text": "A block on a pulley...",
            "related": [
                {"question_id": "q2", "type": "near_duplicate", "confidence": 0.95, "reason": "reworded"}
            ],
        },
    }

    async def fake_execute_tool(name, arguments):
        return tool_results[name]

    result = await run_agent("Tell me about q1", chat_fn=fake_chat, execute_tool_fn=fake_execute_tool)

    assert result.tool_calls_made == 2
    assert result.grounded is True
    tool_steps = [s for s in result.steps if s.type == "tool_call"]
    assert [s.tool for s in tool_steps] == ["question_dna_lookup", "question_relationships_lookup"]
    evidence_types = {e.type for e in result.evidence}
    assert evidence_types == {"question_dna", "relationship"}


@pytest.mark.asyncio
async def test_agent_refuses_to_answer_without_any_tool_call():
    """Guardrail: the agent must never answer an exam-content question
    ungrounded. If the model tries to skip tool use entirely, the
    agent must return the safe fallback, not the model's raw text."""

    async def fake_chat(messages, tools):
        return _assistant_message(content="I think pulley questions are about tension, roughly 5 of them.")

    async def fake_execute_tool(name, arguments):
        raise AssertionError("no tool should have been called")

    result = await run_agent("Find pulley questions", chat_fn=fake_chat, execute_tool_fn=fake_execute_tool)

    assert result.grounded is False
    assert result.tool_calls_made == 0
    assert "roughly 5" not in result.answer  # the ungrounded guess must not leak through
    assert "evidence" in result.answer.lower()


@pytest.mark.asyncio
async def test_agent_handles_ollama_connection_failure_gracefully():
    async def fake_chat(messages, tools):
        raise OllamaError("Could not connect to Ollama at http://localhost:11434 -- is it running?")

    async def fake_execute_tool(name, arguments):
        raise AssertionError("tool should not be called if chat fails")

    result = await run_agent("Find pulley questions", chat_fn=fake_chat, execute_tool_fn=fake_execute_tool)

    assert result.grounded is False
    assert result.error is not None
    assert "ollama" in result.answer.lower()
    assert result.tool_calls_made == 0


@pytest.mark.asyncio
async def test_agent_distinguishes_total_failure_from_mid_conversation_failure():
    """If Ollama fails only after evidence was already retrieved, the
    response must say so and must still surface that evidence -- not
    claim Ollama was entirely unreachable."""
    call_index = {"n": 0}

    async def fake_chat(messages, tools):
        call_index["n"] += 1
        if call_index["n"] == 1:
            return _assistant_message(
                tool_calls=[_tool_call("c1", "semantic_pyq_search", {"query": "pulley"})]
            )
        raise OllamaError("Ollama request to /api/chat timed out after 300.0s")

    async def fake_execute_tool(name, arguments):
        return {
            "results": [
                {
                    "question_id": "q1",
                    "similarity": 0.56,
                    "text": "Two blocks connected by a pulley...",
                    "subject": "Physics",
                    "topic": "Mechanics",
                    "source": {"file": "2021.pdf", "page": 1, "question_number": 18, "section": None},
                }
            ]
        }

    result = await run_agent("Find pulley questions", chat_fn=fake_chat, execute_tool_fn=fake_execute_tool)

    assert result.tool_calls_made == 1
    assert len(result.evidence) == 1  # evidence must not be discarded on a later failure
    assert "retrieved evidence" in result.answer.lower()
    assert "unreachable" not in result.answer.lower() and "couldn't reach" not in result.answer.lower()


@pytest.mark.asyncio
async def test_agent_stops_at_max_iterations_without_crashing():
    """If the model keeps calling tools forever, the loop must still
    terminate deterministically and return whatever evidence it has."""

    async def fake_chat(messages, tools):
        return _assistant_message(
            tool_calls=[_tool_call("c", "exam_trends_lookup", {"mode": "trends"})]
        )

    call_counter = {"n": 0}

    async def fake_execute_tool(name, arguments):
        call_counter["n"] += 1
        return {"mode": "trends", "trends": {"total_questions": 10}}

    result = await run_agent(
        "What are the trends?", chat_fn=fake_chat, execute_tool_fn=fake_execute_tool, max_iterations=3
    )

    assert call_counter["n"] == 3
    assert result.tool_calls_made == 3
    assert result.grounded is True  # evidence was gathered, even though no final answer formed
    assert "step limit" in result.answer.lower()


@pytest.mark.asyncio
async def test_tool_arguments_given_as_json_string_are_parsed():
    async def fake_chat(messages, tools):
        if "call" not in fake_chat.__dict__:
            fake_chat.called = True
            return _assistant_message(
                tool_calls=[
                    {
                        "id": "c1",
                        "function": {
                            "name": "exam_trends_lookup",
                            "arguments": '{"mode": "important_topics", "limit": 3}',
                        },
                    }
                ]
            )
        return _assistant_message(content="Top topics retrieved.")

    received = {}

    async def fake_execute_tool(name, arguments):
        received["arguments"] = arguments
        return {"mode": "important_topics", "important_topics": []}

    await run_agent("What topics matter most?", chat_fn=fake_chat, execute_tool_fn=fake_execute_tool)

    assert received["arguments"] == {"mode": "important_topics", "limit": 3}
