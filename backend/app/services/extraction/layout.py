import pdfplumber

# A column split is only accepted if the gutter is at least this
# fraction of the page width, and the gap recurs across several lines
# -- otherwise ordinary word spacing on a single line (or a page with
# very little text) could be mistaken for a column boundary.
MIN_GUTTER_FRACTION = 0.04
CENTER_BAND = (0.3, 0.7)
LINE_TOLERANCE = 3.0
MIN_QUALIFYING_LINES = 3
MIN_QUALIFYING_LINE_FRACTION = 0.4


def _group_words_into_lines(words: list[dict]) -> list[list[dict]]:
    lines: list[dict] = []
    for word in sorted(words, key=lambda w: w["top"]):
        for line in lines:
            if abs(line["top"] - word["top"]) <= LINE_TOLERANCE:
                line["words"].append(word)
                break
        else:
            lines.append({"top": word["top"], "words": [word]})
    return [line["words"] for line in lines]


def _line_gap_candidate(line_words: list[dict], lower: float, upper: float, min_gap: float) -> float | None:
    """Returns the x-center of the widest qualifying whitespace gap in a
    single line of words, using word edges (not midpoints), or None."""
    ordered = sorted(line_words, key=lambda w: w["x0"])
    if len(ordered) < 2:
        return None

    best_gap = 0.0
    best_center: float | None = None

    for a, b in zip(ordered, ordered[1:]):
        gap = b["x0"] - a["x1"]
        if gap <= 0:
            continue
        center = (a["x1"] + b["x0"]) / 2
        if gap > best_gap:
            best_gap = gap
            best_center = center

    if best_center is not None and best_gap >= min_gap and lower <= best_center <= upper:
        return best_center

    return None


def _detect_column_split(words: list[dict], page_width: float) -> float | None:
    """Looks for a vertical gutter that recurs across multiple lines near
    the page's horizontal center. Returns the gutter's x-coordinate for a
    genuine two-column page, otherwise None (single column)."""
    if not words:
        return None

    lines = _group_words_into_lines(words)
    lower = page_width * CENTER_BAND[0]
    upper = page_width * CENTER_BAND[1]
    min_gap = page_width * MIN_GUTTER_FRACTION

    candidates = [
        candidate
        for line_words in lines
        if (candidate := _line_gap_candidate(line_words, lower, upper, min_gap)) is not None
    ]

    required = max(MIN_QUALIFYING_LINES, int(len(lines) * MIN_QUALIFYING_LINE_FRACTION))
    if len(candidates) < required:
        return None

    candidates.sort()
    return candidates[len(candidates) // 2]


def _extract_page_text(page) -> str:
    words = page.extract_words()
    split_x = _detect_column_split(words, float(page.width))

    if split_x is None:
        return page.extract_text() or ""

    left = page.crop((0, 0, split_x, page.height))
    right = page.crop((split_x, 0, page.width, page.height))
    left_text = left.extract_text() or ""
    right_text = right.extract_text() or ""

    return "\n".join(t for t in (left_text, right_text) if t)


def extract_page_texts(file_path: str) -> list[str]:
    """Extracts text for every page, in correct reading order.

    Genuine two-column pages are split at the detected gutter and read
    left-column-then-right-column; single-column pages (the common
    case) are returned via plain extraction, unchanged.
    """
    with pdfplumber.open(file_path) as pdf:
        return [_extract_page_text(page) for page in pdf.pages]
