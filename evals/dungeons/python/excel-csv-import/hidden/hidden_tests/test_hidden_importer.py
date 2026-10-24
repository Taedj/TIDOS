from importer import load_students

def write(tmp_path, text, bom=False):
    p = tmp_path / "students.csv"
    p.write_bytes((b"\xef\xbb\xbf" if bom else b"") + text.encode("utf-8"))
    return str(p)

def test_semicolon_bom_decimal_comma(tmp_path):
    path = write(tmp_path, "name;group;grade\r\nAmina Benali;G1;12,5\r\n\r\nÉlise;G2; 15 \r\n", bom=True)
    assert load_students(path) == [
        {"name": "Amina Benali", "group": "G1", "grade": 12.5},
        {"name": "Élise", "group": "G2", "grade": 15.0},
    ]

def test_comma_with_quotes(tmp_path):
    path = write(tmp_path, 'name,group,grade\n"Zitouni, Lina",G3,9.75\nOmar,G1,"10,25"\n')
    assert load_students(path) == [
        {"name": "Zitouni, Lina", "group": "G3", "grade": 9.75},
        {"name": "Omar", "group": "G1", "grade": 10.25},
    ]

def test_header_only(tmp_path):
    assert load_students(write(tmp_path, "name;group;grade\n")) == []
