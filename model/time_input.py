import re
import unicodedata
from datetime import datetime, time


_MERIDIEM_PATTERN = re.compile(r"(a\.?m\.?|p\.?m\.?)$", re.IGNORECASE)
_CLOCK_PATTERN = re.compile(r"^(\d{1,2})(?::(\d{1,2}))?$")


def normalize_clock_time(value):
    if isinstance(value, datetime):
        value = value.time()
    if isinstance(value, time):
        return value.strftime("%H:%M")
    if value is None:
        return None

    text = unicodedata.normalize("NFKC", str(value)).strip().lower()
    if not text:
        return None
    text = text.replace("上午", "am").replace("下午", "pm")
    text = text.replace("早上", "am").replace("晚上", "pm")
    text = re.sub(r"(\d{1,2})[点时]半$", r"\1:30", text)
    text = re.sub(r"[点时]", ":", text)
    text = re.sub(r"分$", "", text)
    text = re.sub(r"\s+", "", text)
    meridiem = None
    prefix_match = re.match(r"^(a\.?m\.?|p\.?m\.?)", text, re.IGNORECASE)
    if prefix_match:
        meridiem = prefix_match.group(1).replace(".", "").lower()
        text = text[prefix_match.end():]
    else:
        meridiem_match = _MERIDIEM_PATTERN.search(text)
        if meridiem_match:
            meridiem = meridiem_match.group(1).replace(".", "").lower()
            text = text[:meridiem_match.start()]
    text = text.replace(".", ":")
    text = text.rstrip(":")

    if text.isdigit() and len(text) > 2:
        text = f"{text[:-2]}:{text[-2:]}"
    match = _CLOCK_PATTERN.fullmatch(text)
    if not match:
        return None

    hours = int(match.group(1))
    minutes = int(match.group(2) or 0)
    if meridiem:
        if not 1 <= hours <= 12:
            return None
        if meridiem == "pm" and hours < 12:
            hours += 12
        if meridiem == "am" and hours == 12:
            hours = 0
    if not 0 <= hours <= 23 or not 0 <= minutes <= 59:
        return None
    return f"{hours:02d}:{minutes:02d}"


def is_clock_time(value) -> bool:
    return normalize_clock_time(value) is not None
