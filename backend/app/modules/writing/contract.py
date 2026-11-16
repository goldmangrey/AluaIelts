"""Strict assessment contract, revalidated before persistence. Offsets use UTF-16."""

import math
import re
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

Text = Annotated[str, StringConstraints(min_length=3, max_length=1200)]
QUALITY_POLICY = "writing-accuracy-v3"
CRITERIA = ("task_response", "coherence_cohesion", "lexical_resource", "grammar")


def words(text):
    return len(re.findall(r"[^\W_]+(?:['’\-][^\W_]+)*", text, re.UNICODE))


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class Evidence(Strict):
    quote: Text
    start: int = Field(ge=0)
    end: int = Field(gt=0)


class Target(Strict):
    original: Annotated[str, StringConstraints(min_length=1, max_length=1200)]
    replacement: Annotated[str, StringConstraints(min_length=1, max_length=1200)]


class Limitation(Strict):
    description: Text
    impact: Literal["minor", "substantial"]


class Requirement(Strict):
    requirement: Text
    coverage: Literal["addressed", "partial", "missing"]
    explanation: Text


class PositionClaim(Strict):
    claim: Text
    development: Literal["developed", "asserted", "unclear"]
    basis: Text


class TaskUnderstanding(Strict):
    essay_type: Text
    position: Text
    position_development: Text
    position_claims: list[PositionClaim] = Field(min_length=1, max_length=4)
    requirements: list[Requirement] = Field(min_length=1, max_length=6)


class Criterion(Strict):
    name: Literal["task_response", "coherence_cohesion", "lexical_resource", "grammar"]
    rationale_en: Text
    explanation_ru: Text
    strengths: list[Text] | None = Field(default=None, min_length=1, max_length=3)
    limitations: list[Limitation] | None = Field(default=None, max_length=3)
    descriptor_fit: Text | None = None
    evidence: list[Evidence] = Field(min_length=1, max_length=3)
    band: float = Field(ge=0, le=9, multiple_of=0.5)
    improvement: Text | None = None
    target: Target | None = None


class Issue(Evidence):
    category: Literal["grammar_error", "lexical_error", "coherence", "style_suggestion"]
    why: Text
    better: Text
    explanation_ru: Text
    corrected_translation_ru: Text
    target: Target | None = None
    correction_type: Literal["required", "optional"] | None = None
    necessity: Text | None = None


class Improvement(Strict):
    action: Text
    quote: Text
    target: Target | None = None


class Assessment(Strict):
    criteria: list[Criterion] = Field(min_length=4, max_length=4)
    top_improvements: list[Improvement] = Field(max_length=3)
    issues: list[Issue] = Field(max_length=8)
    uncertainty: Text
    quality_policy: Literal["writing-accuracy-v2", "writing-accuracy-v3"] | None = None
    task_understanding: TaskUnderstanding | None = None


def validate_assessment(raw, essay):
    if isinstance(raw, dict) and raw.get("quality_policy") == "writing-accuracy-v4":
        return validate_v4(raw, essay)
    value = Assessment.model_validate(raw)
    if [c.name for c in value.criteria] != list(CRITERIA):
        raise ValueError("criterion_order")
    v3 = value.quality_policy == QUALITY_POLICY
    v2 = v3 or value.quality_policy == "writing-accuracy-v2"
    if v3 and value.task_understanding is None:
        raise ValueError("task_understanding")
    if not v3 and value.task_understanding is not None:
        raise ValueError("schema")
    for criterion in value.criteria:
        if v3:
            if (
                criterion.strengths is None
                or criterion.limitations is None
                or criterion.descriptor_fit is None
            ):
                raise ValueError("analysis")
            # Self-declared substantial limitation conflicts with the Band 9 descriptor.
            # This checks structured consistency; it does not detect or grade essay limitations.
            if criterion.band == 9 and any(
                limitation.impact == "substantial" for limitation in criterion.limitations
            ):
                raise ValueError("rubric_contradiction")
        elif any(
            k in criterion.model_fields_set for k in ("strengths", "limitations", "descriptor_fit")
        ):
            raise ValueError("schema")
        if not v2 and criterion.band < 1:
            raise ValueError("criterion_band")
        if v2:
            if "target" not in criterion.model_fields_set:
                raise ValueError("target")
            if criterion.improvement is None and criterion.target is not None:
                raise ValueError("target")
            validate_target(criterion.target, [e.quote for e in criterion.evidence])
    # Complexity alone is not an IELTS criterion. Fail closed on generic complexity advice.
    advice = [c.improvement for c in value.criteria] + [i.action for i in value.top_improvements]
    generic = re.compile(
        r"\b(?:use|utili[sz]e|incorporate|employ|add|learn)\b.{0,50}"
        r"\b(?:more advanced|more sophisticated|advanced academic)\b.{0,30}"
        r"\b(?:vocabulary|collocations|words|phrases)\b",
        re.I,
    )
    if any(generic.search(action) for action in advice if action is not None):
        raise ValueError("generic_complexity_advice")
    if re.fullmatch(r"(?:none|no uncertainty)[.! ]*", value.uncertainty, re.I):
        raise ValueError("unsupported_certainty")
    encoded = essay.encode("utf-16-le")
    spans = []
    for anchor in [e for c in value.criteria for e in c.evidence] + value.issues:
        if anchor.end <= anchor.start:
            raise ValueError("offset")
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
        if v2:
            validate_target(issue.target, [issue.quote], issue.better, required=True)
            expected = "optional" if issue.category == "style_suggestion" else "required"
            if issue.correction_type != expected or issue.necessity is None:
                raise ValueError("correction_type")
    if len({i.action.strip().lower() for i in value.top_improvements}) != len(
        value.top_improvements
    ):
        raise ValueError("duplicate_improvement")
    for improvement in value.top_improvements:
        if improvement.quote not in essay:
            raise ValueError("improvement_quote")
        if v2:
            if "target" not in improvement.model_fields_set:
                raise ValueError("target")
            validate_target(improvement.target, [improvement.quote])
    # Alua display convention: equal-weight mean rounded to nearest half, ties upward.
    # Public IELTS overall-test rounding is NOT proof of an official Task 2 rounding rule.
    band = math.floor(sum(c.band for c in value.criteria) / 4 * 2 + 0.5) / 2
    return value.model_dump(exclude_unset=True) | {
        "estimated_band": band,
        "feedback_semantics": "NOT VERIFIED",
        "task2_mean": sum(c.band for c in value.criteria) / 4,
        "calibration": "NOT VERIFIED",
        "rubric_version": "ielts-writing-may-2023",
    }


def validate_target(target, quotes, better=None, required=False):
    """Exact containment and field consistency only, never a grammar/semantic verifier."""
    if target is None:
        if required:
            raise ValueError("target")
        return
    if not target.original.strip() or not target.replacement.strip():
        raise ValueError("target")
    if not any(target.original in quote for quote in quotes):
        raise ValueError("target_source_mismatch")
    if target.original == target.replacement:
        raise ValueError("unchanged_target")
    if better is not None and target.replacement not in better:
        raise ValueError("target_replacement_mismatch")


Fragment = Annotated[str, StringConstraints(min_length=1, max_length=1200)]


class V4Criterion(Strict):
    name: Literal["task_response", "coherence_cohesion", "lexical_resource", "grammar"]
    strength: Text
    limitation: Text | None
    descriptor_fit: Text
    evidence: list[Evidence] = Field(min_length=1)
    band: float = Field(ge=0, le=9, multiple_of=0.5)
    improvement: Text | None
    improvement_quote: Text | None


class V4Issue(Strict):
    quote: Fragment
    start: int = Field(ge=0)
    end: int = Field(gt=0)
    category: Literal["grammar_error", "lexical_error"]
    why: Text
    better: Fragment


class V4Assessment(Strict):
    quality_policy: Literal["writing-accuracy-v4"]
    criteria: list[V4Criterion] = Field(min_length=4, max_length=4)
    top_improvements: list[Improvement] = Field(max_length=3)
    issues: list[V4Issue] = Field(max_length=8)
    uncertainty: Text


def validate_v4(raw, essay):
    value = V4Assessment.model_validate(raw)
    if [c.name for c in value.criteria] != list(CRITERIA):
        raise ValueError("criterion_order")
    encoded = essay.encode("utf-16-le")
    for anchor in [e for c in value.criteria for e in c.evidence] + value.issues:
        if anchor.end <= anchor.start or anchor.end * 2 > len(encoded) or not anchor.quote.strip():
            raise ValueError("offset")
        if encoded[anchor.start * 2 : anchor.end * 2].decode("utf-16-le") != anchor.quote:
            raise ValueError("quote_mismatch")
    for criterion in value.criteria:
        if len({(a.start, a.end) for a in criterion.evidence}) != len(criterion.evidence):
            raise ValueError("duplicate_evidence")
        if criterion.improvement is None:
            if criterion.improvement_quote is not None:
                raise ValueError("improvement_evidence")
        elif criterion.improvement_quote not in [e.quote for e in criterion.evidence]:
            raise ValueError("improvement_evidence")
        # Validate every source above, then keep at most three display anchors.
        visible = criterion.evidence[:3]
        selected = next(
            (e for e in criterion.evidence if e.quote == criterion.improvement_quote), None
        )
        if selected is not None and not any(e.quote == selected.quote for e in visible):
            visible[-1] = selected
        criterion.evidence = visible
    expected = [
        dict(action=c.improvement, quote=c.improvement_quote)
        for c in value.criteria
        if c.improvement is not None
    ][:3]
    # No added target/default fields: the top list is a server-derived projection.
    if [i.model_dump(exclude_unset=True) for i in value.top_improvements] != expected:
        raise ValueError("improvement_consistency")
    end = 0
    for issue in sorted(value.issues, key=lambda i: i.start):
        if issue.start < end or issue.better == issue.quote or not issue.better.strip():
            raise ValueError("issue")
        end = issue.end
    mean = sum(c.band for c in value.criteria) / 4
    normalized = value.model_dump()
    normalized["top_improvements"] = expected
    return normalized | dict(
        estimated_band=math.floor(mean * 2 + 0.5) / 2,
        task2_mean=mean,
        calibration="NOT VERIFIED",
        feedback_semantics="NOT VERIFIED",
        rubric_version="ielts-writing-may-2023",
    )
