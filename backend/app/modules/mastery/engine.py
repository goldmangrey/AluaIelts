from datetime import datetime

from app.modules.mastery.models import (
    EvidenceDifficulty,
    EvidenceKind,
    MasteryEvidence,
    MasteryLevel,
    MasteryState,
    MasteryTrend,
    make_state_id,
)

ENGINE_VERSION = 1
EVIDENCE_WEIGHTS = {
    EvidenceKind.RECOGNITION: 0.60,
    EvidenceKind.RECALL: 0.80,
    EvidenceKind.CONTROLLED_USE: 1.00,
    EvidenceKind.ERROR_CORRECTION: 1.00,
    EvidenceKind.CONTRAST: 1.00,
    EvidenceKind.PRODUCTION: 1.25,
}
DIFFICULTY_MULTIPLIERS = {
    EvidenceDifficulty.EASY: 0.90,
    EvidenceDifficulty.STANDARD: 1.00,
    EvidenceDifficulty.HARD: 1.10,
}
MAX_ERROR_TAGS = 20


class MasteryEngine:
    """Pure v1 projection logic suitable for replaying immutable assessment events.

    Lifetime weighted totals are retained for auditability. The current estimate is an
    EWMA: alpha = clamp(0.15 + 0.12 * effective_weight, 0.15, 0.35). This lets recent
    failures matter without erasing a long history.
    """

    def apply(
        self,
        *,
        uid: str,
        evidence: MasteryEvidence,
        current: MasteryState | None,
        applied_at: datetime,
    ) -> MasteryState:
        weight = (
            EVIDENCE_WEIGHTS[evidence.evidence_kind] * DIFFICULTY_MULTIPLIERS[evidence.difficulty]
        )
        previous_score = current.score if current else None
        if previous_score is None:
            score = evidence.outcome
        else:
            alpha = min(0.35, max(0.15, 0.15 + 0.12 * weight))
            score = previous_score * (1 - alpha) + evidence.outcome * alpha

        count = (current.evidence_count if current else 0) + 1
        successful = (current.successful_evidence_count if current else 0) + int(
            evidence.outcome >= 0.75
        )
        failed = (current.failed_evidence_count if current else 0) + int(evidence.outcome < 0.5)
        weighted_success = (
            current.weighted_success_sum if current else 0.0
        ) + evidence.outcome * weight
        weighted_total = (current.weighted_evidence_sum if current else 0.0) + weight
        confidence = min(0.95, weighted_total / 6.0)
        trend = self._trend(previous_score, score, count)
        tags = self._error_tags(current, evidence)
        return MasteryState(
            state_id=make_state_id(evidence.content_type, evidence.content_id, evidence.dimension),
            user_id=uid,
            content_type=evidence.content_type,
            content_id=evidence.content_id,
            dimension=evidence.dimension,
            score=score,
            confidence=confidence,
            evidence_count=count,
            successful_evidence_count=successful,
            failed_evidence_count=failed,
            weighted_success_sum=weighted_success,
            weighted_evidence_sum=weighted_total,
            previous_score=previous_score,
            last_evidence_at=evidence.occurred_at,
            last_success_at=(
                evidence.occurred_at
                if evidence.outcome >= 0.75
                else current.last_success_at
                if current
                else None
            ),
            last_failure_at=(
                evidence.occurred_at
                if evidence.outcome < 0.5
                else current.last_failure_at
                if current
                else None
            ),
            level=self.level_for(score, confidence, count),
            trend=trend,
            error_tag_counts=tags,
            created_at=current.created_at if current else applied_at,
            updated_at=applied_at,
            engine_version=ENGINE_VERSION,
        )

    @staticmethod
    def level_for(score: float | None, confidence: float, evidence_count: int) -> MasteryLevel:
        if score is None or evidence_count == 0:
            return MasteryLevel.UNASSESSED
        if score >= 0.88 and evidence_count >= 6 and confidence >= 0.75:
            return MasteryLevel.STRONG
        if score >= 0.72 and evidence_count >= 3 and confidence >= 0.40:
            return MasteryLevel.COMPETENT
        return MasteryLevel.DEVELOPING

    @staticmethod
    def is_content_mastered_for_curriculum(
        score: float | None, confidence: float, evidence_count: int
    ) -> bool:
        return score is not None and score >= 0.72 and confidence >= 0.60 and evidence_count >= 4

    @staticmethod
    def _trend(previous: float | None, current: float, count: int) -> MasteryTrend:
        if previous is None or count < 3:
            return MasteryTrend.UNKNOWN
        delta = current - previous
        if delta >= 0.04:
            return MasteryTrend.IMPROVING
        if delta <= -0.04:
            return MasteryTrend.DECLINING
        return MasteryTrend.STABLE

    @staticmethod
    def _error_tags(current: MasteryState | None, evidence: MasteryEvidence) -> dict[str, int]:
        counts = dict(current.error_tag_counts) if current else {}
        if evidence.outcome < 0.75:
            for tag in evidence.error_tags:
                counts[tag] = counts.get(tag, 0) + 1
        ranked = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
        return dict(ranked[:MAX_ERROR_TAGS])
