from datetime import UTC, datetime

from app.core.exceptions import ConflictError
from app.modules.curriculum.content_repository import CurriculumContentRepository
from app.modules.curriculum.models import (
    CurriculumNode,
    CurriculumNodeProgress,
    CurriculumNodeStatus,
    CurriculumProgram,
    CurriculumStage,
    CurriculumStageProgress,
    UserCurriculumOverview,
    UserCurriculumState,
)
from app.modules.curriculum.user_state_repository import UserCurriculumRepository
from app.modules.learning_events.service import LearningEventService
from app.modules.users.models import EnglishLevel, UserProfile
from app.modules.users.repository import UserRepository


class CurriculumService:
    def __init__(
        self,
        content: CurriculumContentRepository,
        state_repository: UserCurriculumRepository,
        user_repository: UserRepository,
        learning_events: LearningEventService,
    ) -> None:
        self._content = content
        self._states = state_repository
        self._users = user_repository
        self._learning_events = learning_events

    def get_program(self) -> CurriculumProgram:
        return self._content.program

    def get_stage(self, stage_id: str) -> CurriculumStage:
        return self._content.get_stage(stage_id)

    def get_node(self, node_id: str) -> CurriculumNode:
        return self._content.get_node(node_id)

    def get_user_curriculum(self, uid: str) -> UserCurriculumOverview:
        profile = self._users.get_by_uid(uid)
        state = self.get_or_create_user_state(uid, profile)
        return self._build_overview(state)

    def get_or_create_user_state(
        self,
        uid: str,
        profile: UserProfile | None,
    ) -> UserCurriculumState:
        existing = self._states.get(uid)
        if existing is not None:
            return existing
        now = datetime.now(UTC)
        state = UserCurriculumState(
            program_id=self._content.program.id,
            curriculum_version=self._content.program.version,
            recommended_stage_id=self._recommended_stage(
                profile.current_level if profile else None
            ),
            created_at=now,
            updated_at=now,
        )
        try:
            return self._states.create(uid, state)
        except ConflictError:
            concurrent_state = self._states.get(uid)
            if concurrent_state is None:
                raise
            return concurrent_state

    def start_node(self, uid: str, node_id: str) -> UserCurriculumOverview:
        node = self._content.get_node(node_id)
        profile = self._users.get_by_uid(uid)
        state = self.get_or_create_user_state(uid, profile)
        statuses = self.get_node_statuses(state)
        status = statuses[node.id]
        if status == CurriculumNodeStatus.LOCKED:
            raise ConflictError(
                message="Complete this node's prerequisites first.",
                code="curriculum_node_locked",
            )
        if status == CurriculumNodeStatus.COMPLETED:
            raise ConflictError(
                message="This curriculum node is already completed.",
                code="curriculum_node_completed",
            )
        started = list(dict.fromkeys([*state.started_node_ids, node.id]))
        updated = self._states.update(
            uid,
            {
                "active_node_id": node.id,
                "started_node_ids": started,
                "updated_at": datetime.now(UTC),
            },
        )
        self._learning_events.record_curriculum_node_started(uid, node.id)
        return self._build_overview(updated)

    def get_node_statuses(self, state: UserCurriculumState) -> dict[str, CurriculumNodeStatus]:
        completed = set(state.completed_node_ids)
        statuses: dict[str, CurriculumNodeStatus] = {}
        for stage in self._content.program.stages:
            for node in stage.nodes:
                if node.id in completed:
                    status = CurriculumNodeStatus.COMPLETED
                elif node.id == state.active_node_id:
                    status = CurriculumNodeStatus.ACTIVE
                elif set(node.prerequisites).issubset(completed):
                    status = CurriculumNodeStatus.AVAILABLE
                else:
                    status = CurriculumNodeStatus.LOCKED
                statuses[node.id] = status
        return statuses

    def get_recommended_next_nodes(
        self,
        state: UserCurriculumState,
        limit: int = 3,
    ) -> list[CurriculumNode]:
        statuses = self.get_node_statuses(state)
        ordered_nodes = [node for stage in self._content.program.stages for node in stage.nodes]
        if state.active_node_id:
            active = self._content.get_node(state.active_node_id)
            remaining = [
                node
                for node in ordered_nodes
                if node.id != active.id
                and node.required
                and statuses[node.id] == CurriculumNodeStatus.AVAILABLE
            ]
            return [active, *remaining][:limit]
        return [
            node
            for node in ordered_nodes
            if node.required and statuses[node.id] == CurriculumNodeStatus.AVAILABLE
        ][:limit]

    def _build_overview(self, state: UserCurriculumState) -> UserCurriculumOverview:
        statuses = self.get_node_statuses(state)
        recommendations = self.get_recommended_next_nodes(state)
        recommendation_ids = {node.id for node in recommendations}
        stages = [
            CurriculumStageProgress(
                stage=stage,
                nodes=[
                    CurriculumNodeProgress(
                        node=node,
                        status=statuses[node.id],
                        is_recommended=node.id in recommendation_ids,
                    )
                    for node in stage.nodes
                ],
            )
            for stage in self._content.program.stages
        ]
        return UserCurriculumOverview(
            program_id=self._content.program.id,
            curriculum_version=self._content.program.version,
            version_label=self._content.program.version_label,
            recommended_stage_id=state.recommended_stage_id,
            active_node_id=state.active_node_id,
            state=state,
            stages=stages,
            recommended_next_nodes=recommendations,
        )

    @staticmethod
    def _recommended_stage(level: EnglishLevel | None) -> str:
        if level is None:
            return "foundation_a1"
        stages: dict[EnglishLevel, str] = {
            EnglishLevel.A1: "foundation_a1",
            EnglishLevel.A2: "core_a2",
            EnglishLevel.B1: "intermediate_b1",
            EnglishLevel.B2: "upper_intermediate_b2",
            EnglishLevel.C1: "ielts_academic",
            EnglishLevel.C2: "ielts_academic",
        }
        return stages[level]
