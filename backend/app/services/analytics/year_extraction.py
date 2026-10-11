import re

# Matches a plausible exam year (1900-2099) anywhere in a filename, e.g.
# "JEE_Main_2024_Shift_1.pdf" or "2021_1_English.pdf".
YEAR_PATTERN = re.compile(r"(?:19|20)\d{2}")


def extract_year(filename: str) -> int | None:
    match = YEAR_PATTERN.search(filename)
    return int(match.group(0)) if match else None
