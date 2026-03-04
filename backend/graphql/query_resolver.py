"""
GraphQL resolvers for Queries.

These resolvers:
- Return results

They contain NO business logic.
"""

import strawberry
from typing import List, Optional
from strawberry.types import Info
from datetime import datetime

# from backend.core.scalars import DecimalScalar
from backend.graphql.schema_types import Grocery, GroceryConnection, GroceryCursorSearch, GroceryCursorInput, GroceryFilterCursorInput, GroceryFilteredConnection
from backend.services import grocery_services as grocery_service


# ============================
# All Queries
# ============================

@strawberry.type
class GroceryQuery:

    @strawberry.field
    async def groceries(
        self,
        info: Info,
        limit: int
    ) -> List[Grocery]:
        return await grocery_service.list_groceries(
            info.context,
            limit
        )

    @strawberry.field
    async def grocery(
        self,
        info: Info,
        id: int
    ) -> Optional[Grocery]:
        return await grocery_service.get_grocery(
            info.context,
            id
        )

    @strawberry.field
    async def searchgroceries(
        self,
        info: Info,
        name: str
    ) -> List[Grocery]:
        return await grocery_service.search_grocery(
            info.context,
            name
        )
    

    @strawberry.field
    async def filtergroceries(
        self,
        info: Info,
        limit:Optional[int] = None,
        offset: Optional[int] = None, 
        sortby: Optional[str] = None,
        sortorder: Optional[str] = None,
        sortdate: Optional[str] = None,
        sortprice: Optional[float] = None,
    ) -> List[Grocery]:
        return await grocery_service.grocery_filter(
            info.context,
            limit,
            offset,
            sortby,
            sortorder,
            sortdate, 
            sortprice
        )
    

    @strawberry.field
    async def searchSuggestions(
            self,
            info: Info,
            name: str
        ) -> List[Grocery]:
            return await grocery_service.searchSuggestions(
                info.context,
                name
            )

    @strawberry.field
    async def pagiGroceryList(
            self,
            info: Info,
            page: int,
            page_size: int
        ) -> List[Grocery]:
            return await grocery_service.listGroceries(
                info.context,
                page,
                page_size
            )

    @strawberry.field
    async def groceries_cursor(
        self,
        info,
        limit: int = 20,
        cursor: Optional[int] = None,
    ) -> GroceryConnection:
        return await grocery_service.listGroceriesCursor(info.context, limit, cursor)
    

    @strawberry.field
    async def groceries_search_cursor(
        self,
        info,
        name: Optional[str] = None,
        limit: int = 20,
        cursor: Optional[GroceryCursorInput] = None,
    ) -> GroceryCursorSearch:
        return await grocery_service.searchGroceriesCursor(
            info.context,
            name,
            limit,
            cursor,
        )

    @strawberry.field
    async def groceries_filtered_cursor(
        self,
        info,
        limit: int = 20,
        sort_by: str = "id",
        sort_order: str = "ASC",
        filter_datetime: Optional[datetime] = None,
        filter_price: Optional[float] = None,
        cursor: Optional[GroceryFilterCursorInput] = None,
    ) -> GroceryFilteredConnection:

        return await grocery_service.listGroceriesFilteredCursor(
            info.context,
            limit,
            sort_by,
            sort_order,
            filter_datetime,
            filter_price,
            cursor,
        )