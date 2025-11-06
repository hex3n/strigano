import re

def extract_strings(filepath, min_length=4):
    """
    Extract ASCII and UTF-16LE strings from a binary file.
    Returns (ascii_strings, unicode_strings)
    """
    ascii_re = re.compile(rb"[\x20-\x7e]{%d,}" % min_length)
    unicode_re = re.compile((rb"(?:[\x20-\x7e]\x00){%d,}" % min_length))

    with open(filepath, "rb") as f:
        data = f.read()

    ascii_found = [s.decode("ascii", errors="ignore") for s in ascii_re.findall(data)]
    unicode_found = [s.decode("utf-16le", errors="ignore") for s in unicode_re.findall(data)]

    return ascii_found, unicode_found
