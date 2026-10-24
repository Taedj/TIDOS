import csv


def load_students(path):
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        text = f.read()
    lines = text.splitlines()
    header = next((line for line in lines if line.strip()), "")
    delimiter = ";" if header.count(";") > header.count(",") else ","
    rows = [r for r in csv.reader(lines, delimiter=delimiter) if any(c.strip() for c in r)]
    students = []
    for row in rows[1:]:
        name, group, grade = (c.strip() for c in row[:3])
        students.append({"name": name, "group": group, "grade": float(grade.replace(",", "."))})
    return students
