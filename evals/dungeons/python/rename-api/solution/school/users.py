import warnings

USERS = {1: "Lina", 2: "Omar"}


def fetch_user(user_id):
    """Return the user's name, or raise KeyError."""
    return USERS[user_id]


def get_user(user_id):
    """Deprecated: use fetch_user()."""
    warnings.warn("get_user() is deprecated, use fetch_user()", DeprecationWarning, stacklevel=2)
    return fetch_user(user_id)
