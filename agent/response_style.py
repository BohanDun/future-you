import re

_LEADING_GREETING = re.compile(
    r"^(?:hi|hello|hey|dear)\s+[^,!\n]{1,80}[,!]\s*",
    re.IGNORECASE,
)
_SIGN_OFF = re.compile(
    r"(?:^|\n)\s*(?:best(?: regards)?|kind regards|regards|sincerely|cheers|thanks)"
    r"\s*[,!]?\s*(?:\n|$)",
    re.IGNORECASE,
)
_TEMPLATE_PLACEHOLDER = re.compile(
    r"\s*(?:\[(?:your )?(?:name|signature)\]|<(?:your )?(?:name|signature)>)\s*",
    re.IGNORECASE,
)


def normalize_chat_response(text: str) -> str:
    """Keep model output in a compact chat reply instead of letter format."""
    cleaned = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    cleaned = _LEADING_GREETING.sub("", cleaned, count=1)

    sign_off = _SIGN_OFF.search(cleaned)
    if sign_off:
        cleaned = cleaned[: sign_off.start()]

    cleaned = _TEMPLATE_PLACEHOLDER.sub(" ", cleaned)
    return re.sub(r"\s+", " ", cleaned).strip()
