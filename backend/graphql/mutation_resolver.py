"""
GraphQL resolvers for mutation.

These resolvers:
- Validate GraphQL inputs
- Call services.grocery
- Return results

They contain NO business logic.
"""

import strawberry
from typing import List, Optional
from strawberry.types import Info

# from backend.core.scalars import DecimalScalar
from backend.graphql.schema_types import Grocery, DeleteResult
from backend.services import grocery_services as grocery_service


# ============================
# All Mutations
# ============================

@strawberry.type
class GroceryMutation:

    @strawberry.mutation
    async def addGrocery(
        self,
        info: Info,
        grocery: str,
        description: str,
        price: str,
    ) -> Grocery:
        return await grocery_service.add_grocery(
            info.context,
            grocery,
            description,
            price,
        )

    @strawberry.mutation
    async def editGrocery(
        self,
        info: Info,
        ID: int,
        grocery: str,
        description: str,
        price: str,
    ) -> Grocery:
        return await grocery_service.edit_grocery(
            info.context,
            ID,
            grocery,
            description,
            price,
        )

    @strawberry.mutation
    async def deleteGrocery(
        self,
        info: Info,
        ID: int,
    ) -> DeleteResult:
        return await grocery_service.delete_grocery(
            info.context,
            ID,
        )
