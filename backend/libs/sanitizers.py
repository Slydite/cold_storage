import re

def clean_text(value: str | None) -> str:
    """
    Strip leading/trailing whitespace, collapse internal runs of whitespace to a single space.
    Returns '' for None or whitespace-only input.
    """
    if not value:
        return ''
    return re.sub(r'\s+', ' ', str(value)).strip()


def title_name(value: str | None) -> str:
    """
    Clean text and convert human names to Title Case while handling hyphenated names,
    apostrophes, and preserving mixed-case words or acronyms (e.g. "GD Foods" stays "GD Foods").
    
    Decision: Uses a conservative title case rule. For each word (space-separated):
    1. If the word contains hyphens or apostrophes, split on those delimiters, title-case
       lowercase/all-caps parts, and re-join.
    2. If a word is entirely lowercase, capitalize the first letter.
    3. If a word is entirely uppercase and longer than 2 letters, title-case it (e.g. "PRAKASH" -> "Prakash").
    4. Otherwise (e.g. 2-letter uppercase acronyms like "GD", or mixed-case like "McDonald"), leave untouched.
    """
    cleaned = clean_text(value)
    if not cleaned:
        return ''

    def _title_word(w: str) -> str:
        if not w:
            return ''
        if '-' in w:
            return '-'.join(_title_word(part) for part in w.split('-'))
        if "'" in w:
            return "'".join(_title_word(part) for part in w.split("'"))
        if "’" in w:
            return "’".join(_title_word(part) for part in w.split("’"))

        if w.islower():
            return w.capitalize()
        if w.isupper() and len(w) > 2:
            return w.capitalize()
        return w

    words = cleaned.split(' ')
    return ' '.join(_title_word(w) for w in words)


def upper_code(value: str | None) -> str:
    """
    Clean text and uppercase. For codes, GSTIN, vehicle numbers, IFSC.
    """
    return clean_text(value).upper()


def clean_gstin(value: str | None) -> str:
    """
    Clean and uppercase GSTIN. Returns '' if blank.
    """
    return upper_code(value)


def clean_phone(value: str | None) -> str:
    """
    Keep digits, '+' and spaces; replace other punctuation (parentheses,
    hyphens, etc.) with a space so digit groups stay separated; collapse
    whitespace.
    """
    if not value:
        return ''
    filtered = ''.join(c if (c.isdigit() or c in ('+', ' ')) else ' ' for c in str(value))
    return clean_text(filtered)


def clean_email(value: str | None) -> str:
    """
    Clean text and lowercase email address.
    """
    return clean_text(value).lower()
