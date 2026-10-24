from names import sort_names

def test_class_list():
    names = ["Zoé", "élodie", "Emma", "Eda", " Ariane", "Œdipe", "Odile", "côte", "cote", "Côte"]
    assert sort_names(names) == [" Ariane", "cote", "côte", "Côte", "Eda", "élodie", "Emma",
                                 "Odile", "Œdipe", "Zoé"]

def test_cedilla_and_ligature():
    assert sort_names(["Çelik", "Cyril", "Cela", "Aëlle", "Aeron", "Æsop"]) == \
        ["Aëlle", "Aeron", "Æsop", "Cela", "Çelik", "Cyril"]

def test_new_list():
    data = ["b", "a"]
    assert sort_names(data) == ["a", "b"] and data == ["b", "a"]
