import strawberry


from .EventGQLModel import EventMutation
from .EventInvitationGQLModel import EventInvitationMutation
from .NoteGQLModel import NoteMutation

@strawberry.type(description="""Type for mutation root""")
class Mutation(EventMutation, EventInvitationMutation, NoteMutation):
    pass
