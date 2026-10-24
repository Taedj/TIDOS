def add_tag(tag, tags=[]):
    """Append tag to tags and return the list."""
    tags.append(tag)
    return tags


class Course:
    def __init__(self, name, students=[]):
        self.name = name
        self.students = students

    def enroll(self, student):
        self.students.append(student)
