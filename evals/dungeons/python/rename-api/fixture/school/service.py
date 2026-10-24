from .users import get_user


def welcome_message(user_id):
    return "Welcome, %s!" % get_user(user_id)
