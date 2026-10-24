def final_grade(marks, weights):
    return sum(m * w for m, w in zip(marks, weights)) / sum(weights)
