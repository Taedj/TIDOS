from datetime import datetime


def parse_date(text):
    return datetime.strptime(text, "%m/%d/%Y").date()


def format_date(value):
    return value.strftime("%m/%d/%Y")
