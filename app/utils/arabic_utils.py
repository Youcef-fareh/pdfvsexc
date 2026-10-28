"""Arabic / RTL text reshaping utilities."""
from __future__ import annotations

try:
    import arabic_reshaper
    from bidi.algorithm import get_display
    _ARABIC_AVAILABLE = True
except ImportError:
    _ARABIC_AVAILABLE = False


def reshape_arabic(text: str) -> str:
    """
    Reshape and apply BiDi algorithm to Arabic text so it renders correctly
    in left-to-right display contexts (e.g., table cells, DOCX paragraphs).

    Falls back to returning the original string if the libraries are unavailable.
    """
    if not text or not _ARABIC_AVAILABLE:
        return text

    try:
        configuration = {
            "delete_harakat": True,      # Remove diacritics — cleaner in tables
            "support_ligatures": True,
            "RIAL SIGN": True,
        }
        reshaped = arabic_reshaper.reshape(text, configuration)
        return get_display(reshaped)
    except Exception:
        return text


def contains_arabic(text: str) -> bool:
    """Return True if the string contains any Arabic Unicode characters."""
    return any("\u0600" <= ch <= "\u06FF" for ch in text)


def is_rtl_dominant(text: str) -> bool:
    """
    Heuristic: consider text RTL if more than 30 % of alpha chars are Arabic.
    Used to set cell alignment in exports.
    """
    if not text:
        return False
    alpha_chars = [ch for ch in text if ch.isalpha()]
    if not alpha_chars:
        return False
    arabic_count = sum(1 for ch in alpha_chars if "\u0600" <= ch <= "\u06FF")
    return (arabic_count / len(alpha_chars)) > 0.30


def process_cell_text(text: str) -> str:
    """
    Full pipeline for a single cell: reshape Arabic if present, leave others.
    This is the main function called by the normalizer.
    """
    if contains_arabic(text):
        return reshape_arabic(text)
    return text
