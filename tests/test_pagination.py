from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parents[1]))

from backend.utils.pagination import (  # noqa: E402
    DEFAULT_PAGE_SIZE,
    MAX_PAGE_SIZE,
    normalize_pagination,
)


def test_normalize_pagination_clamps_page_below_one_to_one() -> None:
    pagination = normalize_pagination(page=0, page_size=10)

    assert pagination.page == 1
    assert pagination.page_size == 10


def test_normalize_pagination_resets_page_size_below_one_to_default() -> None:
    pagination = normalize_pagination(page=2, page_size=0)

    assert pagination.page == 2
    assert pagination.page_size == DEFAULT_PAGE_SIZE


def test_normalize_pagination_clamps_page_size_above_max() -> None:
    pagination = normalize_pagination(page=3, page_size=MAX_PAGE_SIZE + 1)

    assert pagination.page == 3
    assert pagination.page_size == MAX_PAGE_SIZE


def test_normalize_pagination_keeps_valid_values() -> None:
    pagination = normalize_pagination(page=4, page_size=25)

    assert pagination.page == 4
    assert pagination.page_size == 25
