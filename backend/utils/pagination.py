from dataclasses import dataclass

DEFAULT_PAGE = 1
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100


@dataclass(frozen=True)
class Pagination:
    page: int
    page_size: int

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size

    @property
    def limit(self) -> int:
        return self.page_size


def normalize_pagination(page: int | None, page_size: int | None) -> Pagination:
    p = page or DEFAULT_PAGE
    ps = page_size or DEFAULT_PAGE_SIZE

    if p < 1:
        p = 1

    if ps < 1:
        ps = DEFAULT_PAGE_SIZE
    elif ps > MAX_PAGE_SIZE:
        ps = MAX_PAGE_SIZE

    return Pagination(page=p, page_size=ps)


def paginated_cache_key(namespace: str, *, page: int, page_size: int, extra: str = "") -> str:
    # Example:
    # grocery:list:page=1:size=20
    # grocery:list:page=2:size=20:search=apple
    base = f"{namespace}:page={page}:size={page_size}"
    if extra:
        return f"{base}:{extra}"
    return base
