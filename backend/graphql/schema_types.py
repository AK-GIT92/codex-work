"""
GraphQL types for the Grocery domain.

This file defines:
- How Grocery looks to the outside world
- What fields the API returns
- Delete result shape

No business logic belongs here.
"""

import strawberry
from decimal import Decimal
from datetime import datetime
from typing import List, Optional

# from backend.core.scalars import DecimalScalar, DateTimeUTC

@strawberry.type
class Grocery:
    groceryID: int
    groceryName: str
    groceryDescription: str
    groceryPrice: str
    groceryOrderTime: str


@strawberry.type
class DeleteResult:
    groceryID: int


@strawberry.type
class SearchSuggestion:
    groceryName: str


@strawberry.type
class GroceryConnection:
    items: List[Grocery]
    nextCursor: Optional[int]


@strawberry.type
class GroceryCursor:
    time: datetime
    id: int

@strawberry.type
class GroceryCursorSearch:
    items: List[Grocery]
    nextCursor: Optional[GroceryCursor]
    

@strawberry.input
class GroceryCursorInput:
    time: datetime
    id: int


@strawberry.type
class GroceryFilterCursor:
    value: str   # sort value (price, time, or id as string)
    id: int


@strawberry.input
class GroceryFilterCursorInput:
    value: str
    id: int


@strawberry.type
class GroceryFilteredConnection:
    items: List[Grocery]
    nextCursor: Optional[GroceryFilterCursor]