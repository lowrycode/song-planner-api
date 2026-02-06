def get_effective_activity_ids(
    allowed_activity_ids: set[int],
    filter_activity_ids: set[int] | None,
) -> set[int]:
    if not filter_activity_ids:
        return allowed_activity_ids

    return allowed_activity_ids & filter_activity_ids
