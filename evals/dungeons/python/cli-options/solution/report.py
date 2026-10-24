import argparse
import json


def positive_int(value):
    number = int(value)
    if number < 1:
        raise argparse.ArgumentTypeError("must be >= 1")
    return number


def main(argv=None):
    parser = argparse.ArgumentParser(description="Print students by grade")
    parser.add_argument("data", help="JSON file: list of {name, grade}")
    parser.add_argument("--limit", type=positive_int, default=None)
    parser.add_argument("--min-grade", type=float, default=None)
    args = parser.parse_args(argv)
    with open(args.data, encoding="utf-8") as f:
        students = json.load(f)
    if args.min_grade is not None:
        students = [s for s in students if s["grade"] >= args.min_grade]
    ranked = sorted(students, key=lambda s: s["grade"], reverse=True)
    for s in ranked[:args.limit]:
        print("%s: %s" % (s["name"], s["grade"]))


if __name__ == "__main__":
    main()
