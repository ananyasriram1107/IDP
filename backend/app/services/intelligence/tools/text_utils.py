MAX_EVIDENCE_TEXT_CHARS = 500


def truncate_text(text: str, max_chars: int = MAX_EVIDENCE_TEXT_CHARS) -> str:
    """Caps question text returned to the agent.

    Some stored questions (e.g. from PDFs with extraction issues) can be
    thousands of characters long, which bloats the tool-result JSON fed
    back into the LLM's context and slows down an already CPU-bound
    model. Evidence snippets don't need the full text to be useful.
    """
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rstrip() + "..."
