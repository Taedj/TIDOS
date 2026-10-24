from text_utils import slugify

def test_examples():
    assert slugify("  Écoles d'Été — Algérie 2026! ") == "ecoles-d-ete-algerie-2026"
    assert slugify("Ça marche") == "ca-marche"
    assert slugify("Déjà vu!!") == "deja-vu"
    assert slugify("Hello World") == "hello-world"
    assert slugify("a__b") == "a-b"
    assert slugify("naïve café") == "naive-cafe"

def test_edges():
    assert slugify("---") == ""
    assert slugify("") == ""
    assert slugify("ABC123") == "abc123"
