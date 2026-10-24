import re


def render(template, variables):
    return template.format(**variables)


def check(rule, answer, variables):
    kind = rule["type"]
    if kind == "exacte":
        return answer.strip() == render(rule["expected"], variables)
    if kind == "contient":
        return render(rule["expected"], variables).lower() in answer.lower()
    if kind == "regex":
        return re.fullmatch(render(rule["expected"], variables), answer.strip()) is not None
    if kind == "choix":
        return answer.strip() in rule["options"] and answer.strip() == rule["expected"]
    raise ValueError("unknown rule type: %s" % kind)
