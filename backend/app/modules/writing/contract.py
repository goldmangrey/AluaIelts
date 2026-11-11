"""Strict assessment contract, revalidated before persistence. Offsets use UTF-16."""

import math
import re
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

Text = Annotated[str, StringConstraints(min_length=3, max_length=1200)]
CRITERIA = ("task_response", "coherence_cohesion", "lexical_resource", "grammar")


def words(text):
    return len(re.findall(r"[^\W_]+(?:['’\-][^\W_]+)*", text, re.UNICODE))


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class Evidence(Strict):
    quote: Text
    start: int = Field(ge=0)
    end: int = Field(gt=0)


class Criterion(Strict):
    name: Literal["task_response", "coherence_cohesion", "lexical_resource", "grammar"]
    band: float = Field(ge=1, le=9, multiple_of=0.5)
    rationale_en: Text
    explanation_ru: Text
    evidence: list[Evidence] = Field(min_length=1, max_length=3)
    improvement: Text


class Issue(Evidence):
    category: Literal["grammar_error", "lexical_error", "coherence", "style_suggestion"]
    why: Text
    better: Text
    explanation_ru: Text
    corrected_translation_ru: Text


class Improvement(Strict):
    action: Text
    quote: Text


class Assessment(Strict):
    criteria: list[Criterion] = Field(min_length=4, max_length=4)
    top_improvements: list[Improvement] = Field(min_length=3, max_length=3)
    issues: list[Issue] = Field(max_length=8)
    uncertainty: Text


def validate_assessment(raw, essay):
    value = Assessment.model_validate(raw)
    if [c.name for c in value.criteria] != list(CRITERIA):
        raise ValueError("criterion_order")
    # Complexity alone is not an IELTS criterion. Fail closed on generic complexity advice.
    advice = [c.improvement for c in value.criteria] + [i.action for i in value.top_improvements]
    generic = re.compile(
        r"\b(?:use|utili[sz]e|incorporate|employ|add|learn)\b.{0,50}"
        r"\b(?:more advanced|more sophisticated|advanced academic)\b.{0,30}"
        r"\b(?:vocabulary|collocations|words|phrases)\b",
        re.I,
    )
    if any(generic.search(action) for action in advice):
        raise ValueError("generic_complexity_advice")
    if re.fullmatch(r"(?:none|no uncertainty)[.! ]*", value.uncertainty, re.I):
        raise ValueError("unsupported_certainty")
    encoded = essay.encode("utf-16-le")
    spans = []
    for anchor in [e for c in value.criteria for e in c.evidence] + value.issues:
        if anchor.end * 2 > len(encoded):
            raise ValueError("offset")
        if encoded[anchor.start * 2 : anchor.end * 2].decode("utf-16-le") != anchor.quote:
            raise ValueError("quote_mismatch")
    for issue in sorted(value.issues, key=lambda i: i.start):
        if spans and issue.start < spans[-1]:
            raise ValueError("overlapping_issues")
        spans.append(issue.end)
        if issue.better == issue.quote:
            raise ValueError("unchanged_correction")
    if len({i.action.strip().casefold() for i in value.top_improvements}) != 3:
        raise ValueError("duplicate_improvement")
    for improvement in value.top_improvements:
        if improvement.quote not in essay:
            raise ValueError("improvement_quote")
    # Equal weights; nearest half band, ties upward. This is a Task 2 estimate only.
    band = math.floor(sum(c.band for c in value.criteria) / 4 * 2 + 0.5) / 2
    return value.model_dump() | {
        "estimated_band": band,
        "calibration": "NOT VERIFIED",
        "rubric_version": "ielts-writing-may-2023",
    }
