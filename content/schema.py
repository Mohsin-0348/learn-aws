
"""All Schema Will Collect here,
     it is master schema file"""


import graphene
import channels_graphql_ws


class NameInput(graphene.InputObjectType):
    name = graphene.String()
    phone = graphene.Int()


class DemoInput(graphene.InputObjectType):
    room_id = graphene.ID()
    name_input = graphene.List(NameInput)


class SendData(graphene.Mutation):
    success = graphene.Boolean()
    data = graphene.JSONString()

    class Arguments:
        input = DemoInput()

    def mutate(self, info, input, **kwargs):
        print(input['name_input'])
        if 'room_id' in input:
            DemoSubscription.broadcast(payload=input['name_input'], group=input['room_id'])
        return SendData(success=True, data=input['name_input'])


class Query(
    graphene.ObjectType
):
    """All query will in include this class"""
    demo_data = graphene.JSONString()

    def resolve_demo_data(self, info, **kwargs):
        data = [{"name": "user1", "phone": 12345}]
        DemoSubscription.broadcast(payload=data, group="1")
        return data


class Mutation(graphene.ObjectType):
    send_data = SendData.Field()


class DemoSubscription(channels_graphql_ws.Subscription):
    """Simple GraphQL subscription."""

    # Subscription payload.
    room_id = graphene.ID()
    data = graphene.JSONString()

    class Arguments:
        room_id = graphene.ID()

    @staticmethod
    def subscribe(root, info, room_id):
        """Called when user subscribes."""
        print('subscribe', info.context.user)
        return [room_id]

    @staticmethod
    def publish(payload, info, room_id):
        """Called to notify the client."""
        print('publish', info.context.user)
        return DemoSubscription(data=payload, room_id=room_id)


class Subscription(graphene.ObjectType):
    """Root GraphQL subscription."""
    demo_subscription = DemoSubscription.Field()
