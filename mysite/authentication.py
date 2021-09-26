from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone
import jwt
import rsa
import json
import uuid
from decouple import config

from users.models import Client
from chat.models import Participant

User = get_user_model()
N = config("N", None)
E = config("E", None)
D = config("D", None)
P = config("P", None)
Q = config("Q", None)


class TokenManager:

    @staticmethod
    def get_token(exp, payload, token_type="access"):
        exp = timezone.now().timestamp() + (exp * 60)
        return jwt.encode(
            {
                "exp": exp,
                "type": token_type,
                **payload
            }, settings.SECRET_KEY, algorithm="HS256"
        )

    @staticmethod
    def decode_token(token):
        try:
            decoded = jwt.decode(token, key=settings.SECRET_KEY, algorithms="HS256")
        except jwt.DecodeError:
            return None

        if timezone.now().timestamp() > decoded['exp']:
            return None
        return decoded

    @staticmethod
    def decode_client_token(token):
        try:
            decoded = jwt.decode(token, key=settings.CLIENT_KEY, algorithms="HS256")
        except jwt.DecodeError:
            return None

        return decoded

    @staticmethod
    def get_access(payload):
        token_expiration_time = 24 * 60
        return TokenManager.get_token(token_expiration_time, payload)

    @staticmethod
    def get_refresh(payload):
        token_expiration_time = 24 * 60
        token_type = "refresh"
        return TokenManager.get_token(token_expiration_time, payload, token_type)

    @staticmethod
    def get_email(id_token):
        decoded = jwt.decode(id_token, '', verify=False)
        return decoded.get('email')


class Authentication:

    def __init__(self, request):
        self.request = request

    def authenticate(self):
        data = self.validate_request()

        if not data:
            return None

        return self.get_user(data['user_id'])

    def validate_request(self):
        authorization = self.request.headers.get("AUTHORIZATION", None)
        if not authorization:
            return None

        token = authorization[4:]
        decoded_data = TokenManager.decode_token(token)
        if not decoded_data:
            return None
        return decoded_data

    @staticmethod
    def get_user(user_id):
        try:
            user = User.objects.get(id=user_id)
            return user
        except User.DoesNotExist:
            return None


class ClientAuthentication:

    def __init__(self, request):
        self.request = request

    def authenticate(self):
        data = self.validate_request()

        if not data or not data.get('client_id'):
            return None
        client = self.get_client(data['client_id'])
        participant = None
        if client:
            participant = self.get_participant(client, data['user_id'])
        return client, participant

    def channel_auth(self):
        """
            this function will take token from channel request
            and return user data
        """
        data = self.validate_token()

        if not data:
            return None

        client = self.get_client(data['client_id'])
        participant = None
        if client:
            participant = self.get_participant(client, data['user_id'])
        return participant

    def validate_request(self):
        authorization = self.request.headers.get("AUTHORIZATION", None)
        if not authorization:
            return None

        token = authorization
        decoded_data = TokenManager.decode_client_token(token)
        if not decoded_data:
            return None
        # try:
        #     private_key = rsa.PrivateKey(int(N), int(E), int(D), int(P), int(Q))
        #     decoded_data = rsa.decrypt(eval(decoded_data['data']), private_key).decode()
        #     decoded_data = json.loads(decoded_data)
        # except Exception as e:
        #     return None

        return decoded_data

    def validate_token(self):
        """
            this request will be token data
        """
        decoded = TokenManager.decode_client_token(self.request)
        if not decoded:
            return None
        if not decoded:
            return None

        # try:
        #     private_key = rsa.PrivateKey(int(N), int(E), int(D), int(P), int(Q))
        #     decoded = rsa.decrypt(eval(decoded['data']), private_key).decode()
        #     decoded = json.loads(decoded)
        # except Exception as e:
        #     return None

        return decoded

    @staticmethod
    def get_client(client_id):
        try:
            client_id = uuid.UUID(client_id)
            client = Client.objects.get(id=client_id)
            return client
        except Client.DoesNotExist:
            return None

    @staticmethod
    def get_participant(client, participant_id):
        try:
            participant, created = Participant.objects.get_or_create(client=client, user_id=participant_id)
            return participant
        except Exception as e:
            return None
