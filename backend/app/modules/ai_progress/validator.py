from collections.abc import Iterable


def validate_fact_references(returned_ids: Iterable[str], available_fact_ids: set[str]) -> bool:
    return all(fact_id in available_fact_ids for fact_id in returned_ids)


def dedupe_fact_references(returned_ids: Iterable[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(returned_ids))
