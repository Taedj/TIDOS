USERS = {1: "Lina", 2: "Omar"}


def get_user(user_id):
    """Return the user's name, or raise KeyError."""
    return USERS[user_id]
