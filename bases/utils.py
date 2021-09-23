import string
import random
import uuid


def generate_auth_key():
    key = ''.join(random.choice(string.ascii_lowercase + string.digits) for _ in range(20))
    key = 'w3AC' + key
    return key


def create_token():
    return uuid.uuid4()
