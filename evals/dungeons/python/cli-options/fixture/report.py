import argparse
import json


def main(argv=None):
    parser = argparse.ArgumentParser(description="Print students by grade")
    parser.add_argument("data", help="JSON file: list of {name, grade}")
    args = parser.parse_args(argv)
    with open(args.data, encoding="utf-8") as f:
        students = json.load(f)
    for s in sorted(students, key=lambda s: s["grade"], reverse=True):
        print("%s: %s" % (s["name"], s["grade"]))


if __name__ == "__main__":
    main()
