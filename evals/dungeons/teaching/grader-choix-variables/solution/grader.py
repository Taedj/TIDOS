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
        given = answer.strip().lower()
        options = [render(o, variables).strip().lower() for o in rule["options"]]
        return given in options and given == render(rule["expected"], variables).strip().lower()
    raise ValueError("unknown rule type: %s" % kind)
