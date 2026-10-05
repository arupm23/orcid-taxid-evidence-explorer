import re


ORCID_PATTERN = re.compile(r"^(?:https?://orcid\.org/)?(\d{4}-\d{4}-\d{4}-\d{3}[\dX])$", re.I)


def normalize_orcid(value):
    """Return a canonical ORCID iD or raise ValueError."""
    if not isinstance(value, str):
        raise ValueError("ORCID iD must be a string")
    match = ORCID_PATTERN.fullmatch(value.strip())
    if not match:
        raise ValueError("Use an ORCID iD in the form 0000-0000-0000-0000")
    orcid = match.group(1).upper()
    digits = orcid.replace("-", "")
    total = 0
    for character in digits[:-1]:
        total = (total + int(character)) * 2
    remainder = total % 11
    result = (12 - remainder) % 11
    expected = "X" if result == 10 else str(result)
    if digits[-1] != expected:
        raise ValueError("The ORCID checksum is invalid")
    return orcid

