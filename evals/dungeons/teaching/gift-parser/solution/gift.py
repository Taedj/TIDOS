import re

_ESCAPES = {"\\": "\ue000", "~": "\ue001", "=": "\ue002", "#": "\ue003", "{": "\ue004", "}": "\ue005",
            ":": "\ue006"}


def _protect(text):
    return re.sub(r"\\([\\~=#{}:])", lambda m: _ESCAPES[m.group(1)], text)


def _restore(text):
    for char, placeholder in _ESCAPES.items():
        text = text.replace(placeholder, char)
    return text


def _blocks(text):
    blocks, current = [], []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("//"):
            continue
        if not stripped:
            if current:
                blocks.append(current)
                current = []
            continue
        current.append(stripped)
    if current:
        blocks.append(current)
    return blocks


def _question(lines):
    source = _protect(" ".join(lines))
    title = None
    match = re.match(r"::(.*?)::(.*)$", source, re.S)
    if match:
        title = _restore(match.group(1)).strip()
        source = match.group(2)
    start, end = source.find("{"), source.find("}")
    if start < 0 or end < start:
        raise ValueError("question without answer block")
    text = _restore(source[:start]).strip()
    body = source[start + 1:end].strip()
    if not text:
        raise ValueError("question without text")
    if body.upper() in ("T", "TRUE", "F", "FALSE"):
        return {"title": title, "text": text, "type": "tf", "answers": [], "correct": body.upper()[0] == "T"}
    if not body or body[0] not in "=~":
        raise ValueError("invalid answer block")
    options = [(mark, _restore(chunk.split("#", 1)[0]).strip())
               for mark, chunk in re.findall(r"([=~])([^=~]*)", body)]
    if any(mark == "~" for mark, _ in options):
        correct = [t for mark, t in options if mark == "="]
        if len(correct) != 1:
            raise ValueError("multiple choice needs exactly one correct answer")
        return {"title": title, "text": text, "type": "mc", "answers": [t for _, t in options],
                "correct": correct[0]}
    answers = [t for _, t in options]
    return {"title": title, "text": text, "type": "short", "answers": answers, "correct": list(answers)}


def parse_gift(text):
    return [_question(block) for block in _blocks(text)]
