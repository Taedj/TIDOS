from .users import fetch_user


def welcome_message(user_id):
    return "Welcome, %s!" % fetch_user(user_id)
