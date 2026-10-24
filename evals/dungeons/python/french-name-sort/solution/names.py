import unicodedata

_LIGATURES = str.maketrans({"œ": "oe", "Œ": "OE", "æ": "ae", "Æ": "AE"})


def _base(name):
    decomposed = unicodedata.normalize("NFKD", name.strip().translate(_LIGATURES))
    return "".join(c for c in decomposed if not unicodedata.combining(c)).casefold()


def _accents(name):
    return sum(1 for c in unicodedata.normalize("NFD", name) if unicodedata.combining(c))


def sort_names(names):
    return sorted(names, key=lambda n: (_base(n), _accents(n)))
