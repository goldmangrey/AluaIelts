"""Deterministic, private-key Reading scoring. No fuzzy matching or invented synonyms."""

from __future__ import annotations

import collections
import re
import unicodedata

SUPPORTED_RULES = {
    "unicode_nfkc",
    "casefold",
    "trim",
    "collapse_whitespace",
    "normalize_apostrophe",
    "numeric_thousands_separator",
}


def normalize(value: str, rules: list[str]) -> str:
    unknown = set(rules) - SUPPORTED_RULES
    if unknown:
        raise ValueError(f"Unsupported normalization rules: {unknown}")
    if not isinstance(value, str):
        raise TypeError("Answers must be strings")
    if "unicode_nfkc" in rules:
        value = unicodedata.normalize("NFKC", value)
    if "normalize_apostrophe" in rules:
        value = value.translate(str.maketrans({"’": "'", "‘": "'", "ʼ": "'"}))
    if "casefold" in rules:
        value = value.casefold()
    if "trim" in rules:
        value = value.strip()
    if "collapse_whitespace" in rules:
        value = " ".join(value.split())
    if "numeric_thousands_separator" in rules:
        value = re.sub(r"(?<=\d),(?=\d{3}(?:\D|$))", "", value)
    return value


def grade_exam(exam: dict, key: dict, responses: dict[str, str], *, allow_unreleased=False) -> dict:
    """Every position scores <=1; an unordered selection is a multiset with unique submissions.

    Per-position values remain the API contract even for a grouped iOS selector. The client
    sends its selected values under the group's question IDs. A repeated value scores once.
    Unreleased content requires an explicit offline QA flag, never enabled in a route.
    """
    if exam["id"] != key["exam_id"] or exam["dataset_version"] != key["dataset_version"]:
        raise ValueError("Exam/key identity or version mismatch")
    if not allow_unreleased and (exam["content_status"] != "ready" or not exam["source_verified"]):
        raise ValueError("Exam is not released")
    qs = {
        q["id"]: q for p in exam["passages"] for g in p["question_groups"] for q in g["questions"]
    }
    ks = {k["question_id"]: k for k in key["answers"]}
    if set(qs) != set(ks) or len(qs) != 40:
        raise ValueError("Incomplete or mismatched exam")
    if set(responses) - set(qs):
        raise ValueError("Unknown question IDs")
    scored = {}
    seen = set()
    for qid, k in ks.items():
        group = k["grading_group"]
        if not group:
            rules = k["normalization_rules"]
            v = normalize(responses.get(qid, ""), rules)
            if k["grading"]["mode"] == "unordered_parts":
                import itertools

                allowed = set()
                for combination in itertools.product(*k["grading"]["parts"]):
                    for order in itertools.permutations(combination):
                        for separator in [" ", " and ", " & ", " + ", ", "]:
                            allowed.add(normalize(separator.join(order), rules))
                scored[qid] = int(bool(v) and v in allowed)
            else:
                scored[qid] = int(
                    bool(v) and v in {normalize(a, rules) for a in k["accepted_answers"]}
                )
            continue
        if group["id"] in seen:
            continue
        seen.add(group["id"])
        members = [
            m
            for m in key["answers"]
            if m["grading_group"] and m["grading_group"]["id"] == group["id"]
        ]
        # A maximum bipartite matching handles optional words/variants without allowing
        # two submissions to consume the same official answer position.
        submissions = []
        unique = set()
        for member in members:
            mid = member["question_id"]
            v = normalize(responses.get(mid, ""), member["normalization_rules"])
            scored[mid] = 0
            if v and v not in unique:
                submissions.append((mid, v))
                unique.add(v)
        accepted = [
            {normalize(answer, members[0]["normalization_rules"]) for answer in unit}
            for unit in group["expected_units"]
        ]
        match = {}

        def place(si, visited):
            for ai, allowed in enumerate(accepted):
                if ai in visited or submissions[si][1] not in allowed:
                    continue
                visited.add(ai)
                if ai not in match or place(match[ai], visited):
                    match[ai] = si
                    return True
            return False

        for si in range(len(submissions)):
            place(si, set())
        for si in match.values():
            scored[submissions[si][0]] = 1
    breakdown = collections.defaultdict(
        lambda: {"correct": 0, "total": 0, "incorrect_question_ids": []}
    )
    for qid, q in qs.items():
        row = breakdown[q["type"]]
        row["total"] += 1
        row["correct"] += scored[qid]
        if not scored[qid]:
            row["incorrect_question_ids"].append(qid)
    return {
        "exam_id": exam["id"],
        "dataset_version": exam["dataset_version"],
        "score": sum(scored.values()),
        "out_of": 40,
        "positions": scored,
        "by_question_type": dict(breakdown),
    }
