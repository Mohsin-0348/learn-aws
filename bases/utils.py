import string
import random


def generate_auth_key():
    key = ''.join(random.choice(string.ascii_lowercase + string.digits) for _ in range(20))
    key = 'w3AC' + key
    return key
