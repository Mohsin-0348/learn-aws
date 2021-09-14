
from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware

from .authentication import Authentication, ClientAuthentication


@database_sync_to_async
def get_user(token_key):
    try:
        user = ClientAuthentication(token_key).channel_auth()
        return user
    except Exception:
        return None


class W3AuthMiddleware(object):

    def resolve(self, next, root, info, **kwargs):
        info.context.user = self.authorize_user(info)
        if self.authorize_client(info):
            info.context.client, info.context.participant = self.authorize_client(info)
        return next(root, info, **kwargs)

    @staticmethod
    def authorize_user(info):
        auth = Authentication(info.context)
        return auth.authenticate()

    @staticmethod
    def authorize_client(info):
        auth = ClientAuthentication(info.context)
        return auth.authenticate()


class TokenMiddleware(BaseMiddleware):

    def __init__(self, inner):
        print(1, inner)
        self.inner = inner

    async def __call__(self, scope, receive, send):
        try:
            print(True)
            token_key = (dict((x.split('=') for x in scope['query_string'].decode().split("&")))).get('token', None)
            print(2, token_key)
        except ValueError:
            print(3, False)
            token_key = None
        scope['user'] = None if token_key is None else await get_user(token_key)
        return await super().__call__(scope, receive, send)
