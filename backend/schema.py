"""
Strawberry GraphQL schema.

This file:
- Combines all query and mutation classes
- Exposes a single GraphQL schema to FastAPI
"""

import strawberry

from backend.graphql.query_resolver import GroceryQuery
from backend.graphql.mutation_resolver import GroceryMutation

@strawberry.type
class Query(GroceryQuery):
    pass


@strawberry.type
class Mutation(GroceryMutation):
    pass


schema = strawberry.Schema(
    query=Query,
    mutation=Mutation,
)
