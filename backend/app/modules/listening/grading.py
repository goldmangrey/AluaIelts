"""Conservative official-notation interpreter. Unknown syntax is ungradable, not wrong."""

import re
import unicodedata

from app.modules.listening.catalog import questions

BAND_VERSION = "listening-estimate-v1"
BANDS = [
    (39, 9),
    (37, 8.5),
    (35, 8),
    (32, 7.5),
    (30, 7),
    (26, 6.5),
    (23, 6),
    (18, 5.5),
    (16, 5),
    (13, 4.5),
    (10, 4),
    (8, 3.5),
    (6, 3),
    (4, 2.5),
]


def norm(text):
    return " ".join(unicodedata.normalize("NFC", text).casefold().split())


def split_forms(text):
    depth = 0
    start = 0
    parts = []
    for i, c in enumerate(text):
        if c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
            if depth < 0:
                raise ValueError("Unbalanced official parentheses")
        elif c == "/" and depth == 0:
            parts.append(text[start:i])
            start = i + 1
    if depth:
        raise ValueError("Unbalanced official parentheses")
    parts.append(text[start:])
    return parts


def forms(text, _nested=False):
    if re.fullmatch(r"[A-K]", text.strip()):
        return {text.strip().casefold()}
    if re.fullmatch(r"[£$€+-]?\d{1,3}(?:,\d{3})+(?:\.\d+)?", text.strip()):
        return {norm(text)}
    text = re.split(r"\s*\(?IN (?:EITHER|ANY) ORDER", text, flags=re.I)[0].strip()
    # A comma inside an explicit thousands group is not a component separator.
    # Keep the literal spelling in accepted forms; lists such as Monday, Thursday
    # and comma-separated times remain ambiguous and require a typed rule.
    syntax = re.sub(r"(?<=\d),(?=\d{3}(?:\D|$))", "", text)
    if not text or re.search(r"[,;+|\[\]{}]|\b(?:BOTH REQUIRED|OR)\b", syntax):
        raise ValueError("Composite official notation needs an explicit rule")
    result = set()
    for variant in split_forms(text):
        if "(" not in variant:
            result.add(norm(variant))
            continue
        start = variant.index("(")
        depth = 1
        end = start + 1
        while end < len(variant) and depth:
            if variant[end] == "(":
                depth += 1
            if variant[end] == ")":
                depth -= 1
            end += 1
        inside = variant[start + 1 : end - 1]
        prefix = variant[:start]
        suffix = variant[end:]
        options = {""} | forms(inside, True)
        for option in options:
            result.update(forms(prefix + option + suffix, True))
        if len(result) > 256:
            raise ValueError("Official notation expands beyond safe limit")
    if "" in result:
        result.remove("")
    if not _nested and any(v in ("a", "an", "the") for v in result):
        raise ValueError("Ambiguous abbreviation in official key")
    return result


def within_limit(value, q):
    c = q["constraints"]
    tokens = value.strip().split()
    numeric = [t for t in tokens if re.fullmatch(r"[£$€+-]?[\d.,:/-]+(?:st|nd|rd|th)?", t, re.I)]
    words = len(tokens) - len(numeric)
    if numeric and len(numeric) == len(tokens):
        numeric = [value]  # Official phone/postcode spacing is one numeric value.
    if not c.get("allows_number") and numeric:
        return False
    if c.get("max_words") is not None and words > c["max_words"]:
        return False
    if c.get("max_numbers") is not None and len(numeric) > c["max_numbers"]:
        return False
    return True


def official_limit(value, question, accepted):
    # Explicit written-number alternatives are numeric answers in the official key.
    # Accept only enumerated forms; never infer spelling or number equivalents.
    # A printed UK postcode is one answer unit even when its official form has
    # an internal space. Require an exact key match; do not accept guessed codes.
    if norm(value) in accepted and re.fullmatch(r"[a-z]{1,2}\d[a-z\d]? \d[a-z]{2}", norm(value)):
        return within_limit(value.replace(" ", ""), question)
    return within_limit(value, question) or (
        norm(value) in accepted
        and question["constraints"].get("allows_number")
        and any(
            re.fullmatch(r"[£$€+-]?[\d.,:/-]+", form) and within_limit(form, question)
            for form in accepted
        )
    )


def result_for(snapshot, answers):
    exam = snapshot["exam"]
    key = snapshot["key"]
    mode = snapshot["mode"]
    practice = snapshot.get("grading_policy") == "practice-v2"
    qmap = questions(exam)
    keys = {k["question_id"]: k for k in key["answers"]}
    rules = {r["question_id"]: r for r in key.get("within_position_rules", [])}
    scores = {}
    expected = {}
    issues = {}
    if practice or mode != "ungraded":
        for group in key["unordered_groups"]:
            ids = [f"{exam['exam_id']}-q{n:02}" for n in group["question_numbers"]]
            try:
                pool = [forms(unit) for unit in group["expected_units"]]
            except ValueError as error:
                for qid in ids:
                    issues[qid] = str(error)
                    expected[qid] = " + ".join(group["expected_units"])
                continue
            for qid in ids:
                val = answers.get(qid, "")
                matched = next((i for i, unit in enumerate(pool) if norm(val) in unit), None)
                scores[qid] = matched is not None and within_limit(val, qmap[qid][2])
                if scores[qid]:
                    pool.pop(matched)
                expected[qid] = " + ".join(group["expected_units"]) + " (either order)"
        for qid, (_, _, q) in qmap.items():
            if qid in scores or qid in issues:
                continue
            k = keys.get(qid)
            if not k:
                issues[qid] = "Official key unavailable"
                continue
            expected[qid] = k["official_answer"]
            try:
                val = answers.get(qid, "")
                if qid in rules:
                    components = [
                        set().union(*(forms(v) for v in c["explicit_slash_forms"]))
                        for c in rules[qid]["components"]
                    ]
                    # Enumerate word-boundary partitions, then consume unique required components.
                    tokens = val.split()
                    ok = False
                    if len(components) == 2:
                        for i in range(1, len(tokens)):
                            left, right = norm(" ".join(tokens[:i])), norm(" ".join(tokens[i:]))
                            if (left in components[0] and right in components[1]) or (
                                left in components[1] and right in components[0]
                            ):
                                ok = True
                    else:
                        raise ValueError("Composite rule requires further interpretation")
                else:
                    accepted = forms(k["official_answer"])
                    ok = norm(val) in accepted
                scores[qid] = ok and (
                    within_limit(val, q) if qid in rules else official_limit(val, q, accepted)
                )
            except ValueError as error:
                issues[qid] = str(error)
    rows = []
    for qid, (part, _, q) in qmap.items():
        rows.append(
            {
                "question_id": qid,
                "question_number": q["question_number"],
                "part_number": part["part_number"],
                "user_answer": answers.get(qid, ""),
                "correct": scores.get(qid),
                "correct_answer": expected.get(qid),
                "grading_issue": issues.get(qid),
                "key_verified": keys.get(qid, {}).get("verification", {}).get("status")
                == "key_verified",
            }
        )
    scored = len(scores)
    correct = sum(scores.values())
    verified = mode == "verified" and not issues
    band_eligible = (scored == 40 and not issues) if practice else verified
    return {
        "mode": mode,
        "label": "Listening practice"
        if practice
        else "Verified practice"
        if verified
        else "Ungraded practice"
        if mode == "ungraded"
        else "Preliminary result",
        "correct_count": correct if scored else None,
        "total_questions": 40,
        "graded_count": scored,
        "answered_count": sum(bool(v.strip()) for v in answers.values()),
        "accuracy": round(correct / scored * 100, 1) if scored else None,
        "estimated_band": next((band for cutoff, band in BANDS if correct >= cutoff), None)
        if band_eligible
        else None,
        "band_table_version": BAND_VERSION if band_eligible else None,
        "band_reference": "https://ielts.org/take-a-test/your-results/ielts-scoring-in-detail"
        if band_eligible
        else None,
        "band_table": BANDS if band_eligible else None,
        "band_note": (
            "Estimated practice band"
            if practice
            else "Estimated IELTS Band; indicative practice conversion."
        )
        if band_eligible
        else None,
        "grading_issues": issues,
        "questions": rows,
        "parts": [
            {
                "part_number": p,
                "correct": sum(r["correct"] is True for r in rows if r["part_number"] == p)
                if scored
                else None,
                "answered": sum(
                    bool(r["user_answer"].strip()) for r in rows if r["part_number"] == p
                ),
                "total": 10,
                "graded": sum(r["correct"] is not None for r in rows if r["part_number"] == p),
            }
            for p in range(1, 5)
        ],
    }
