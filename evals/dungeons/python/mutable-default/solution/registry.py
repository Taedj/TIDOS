def add_tag(tag, tags=None):
    """Append tag to tags and return the list."""
    if tags is None:
        tags = []
    tags.append(tag)
    return tags


class Course:
    def __init__(self, name, students=None):
        self.name = name
        self.students = list(students) if students is not None else []

    def enroll(self, student):
        self.students.append(student)
