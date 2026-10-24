def paginate(items, page, size):
    """Return the items shown on a 1-based page."""
    start = (page - 1) * size
    return items[start:start + size]


def page_count(items, size):
    """Number of pages needed to show all items."""
    return -(-len(items) // size)
