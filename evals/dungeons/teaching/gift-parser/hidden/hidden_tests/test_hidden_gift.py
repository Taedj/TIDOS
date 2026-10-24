import pytest
from gift import parse_gift

QUIZ = r"""
// course: networks
::Q1:: What does TCP stand for? {
=Transmission Control Protocol#correct!
~Transfer Control Protocol
~Total Control \= Protocol
}

The earth is
flat. {F}


::Port:: Default HTTP port\: ? {=80 =eighty # also fine}

// comment between questions
Is 1 \= 1 ? {TRUE}

Set \{1,2\} is finite {t}
"""

def test_full_quiz():
    assert parse_gift(QUIZ) == [
        {"title": "Q1", "text": "What does TCP stand for?", "type": "mc",
         "answers": ["Transmission Control Protocol", "Transfer Control Protocol", "Total Control = Protocol"],
         "correct": "Transmission Control Protocol"},
        {"title": None, "text": "The earth is flat.", "type": "tf", "answers": [], "correct": False},
        {"title": "Port", "text": "Default HTTP port: ?", "type": "short", "answers": ["80", "eighty"],
         "correct": ["80", "eighty"]},
        {"title": None, "text": "Is 1 = 1 ?", "type": "tf", "answers": [], "correct": True},
        {"title": None, "text": "Set {1,2} is finite", "type": "tf", "answers": [], "correct": True},
    ]

def test_escaped_hash_and_tilde_in_answers():
    [q] = parse_gift(r"Pick {=C\# ~C\~ ~Java#no}")
    assert q["answers"] == ["C#", "C~", "Java"] and q["correct"] == "C#"

@pytest.mark.parametrize("bad", ["No answers here", "Pick {~a ~b}", "Pick {=a ~b =c}", "{T}"])
def test_invalid(bad):
    with pytest.raises(ValueError):
        parse_gift(bad)

def test_empty():
    assert parse_gift("// only a comment\n\n") == []
