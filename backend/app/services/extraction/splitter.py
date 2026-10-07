import re

PAGE_JOINER = "\n"

SECTION_PATTERN = re.compile(r"(?im)^\s*section\s+([0-9]+|[ivxlc]+)\b")

# Two ways a question header tends to appear in PYQ papers:
#   "Q.17 ..." / "Q17 ..." / "Question 17 ..."  (qnum group)
#   "17. ..." / "18) ..."                         (num group)
# Anchored to the start of a (reconstructed) line so ordinary numbers
# inside sentences ("...8.314 J...") are not mistaken for a new question.
QUESTION_START_PATTERN = re.compile(
    r"(?m)^\s*(?:Q(?:uestion)?\.?\s*(?P<qnum>\d{1,3})(?=[\.\):]|\s)"
    r"|(?P<num>\d{1,3})[\.\)]\s+)"
)


def _page_start_offsets(page_texts: list[str]) -> list[int]:
    offsets = []
    offset = 0
    for text in page_texts:
        offsets.append(offset)
        offset += len(text) + len(PAGE_JOINER)
    return offsets


def _page_for_offset(offsets: list[int], position: int) -> int:
    page_number = 1
    for index, offset in enumerate(offsets):
        if position >= offset:
            page_number = index + 1
        else:
            break
    return page_number


def _section_markers(full_text: str) -> list[tuple[int, str]]:
    return [
        (match.start(), f"Section {match.group(1).upper()}")
        for match in SECTION_PATTERN.finditer(full_text)
    ]


def _section_for_offset(markers: list[tuple[int, str]], position: int) -> str | None:
    current: str | None = None
    for offset, label in markers:
        if offset <= position:
            current = label
        else:
            break
    return current


def split_into_questions(page_texts: list[str]) -> list[dict]:
    """Splits extracted page text into individual questions.

    Question numbering commonly restarts within each section of a PYQ
    paper (Section 1 has Q.1..Q.4, Section 2 has Q.5..Q.10, and a
    multi-subject paper repeats this per subject). This function does
    not assume numbers increase monotonically -- it simply follows
    document order and records which section each question fell under,
    so repeated numbers across sections/subjects are expected and kept
    distinguishable via (page, section, question_number).

    Text is joined across the whole document (not handled page-by-page
    in isolation) so a question whose text continues onto the next
    page is still captured in full; the recorded page is the question's
    starting page.
    """
    full_text = PAGE_JOINER.join(page_texts)
    page_offsets = _page_start_offsets(page_texts)
    section_markers = _section_markers(full_text)

    matches = list(QUESTION_START_PATTERN.finditer(full_text))
    results: list[dict] = []

    for i, match in enumerate(matches):
        question_number = int(match.group("qnum") or match.group("num"))
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(full_text)
        text = full_text[start:end].strip()
        if not text:
            continue

        anchor = match.start("qnum") if match.group("qnum") else match.start("num")
        page_number = _page_for_offset(page_offsets, anchor)
        section = _section_for_offset(section_markers, anchor)

        results.append(
            {
                "page": page_number,
                "section": section,
                "question_number": question_number,
                "text": text,
            }
        )

    return results
