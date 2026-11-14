"""신고 절차 데이터(backend/data/*.json) 로딩과 검증. 절차의 단일 출처입니다.

서버가 시작될 때 load_procedures()를 불러 형식이 틀리면 시작을 실패시킵니다.
"""

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal, get_args

from pydantic import BaseModel, ConfigDict

from app.schemas.common import Category, TypeId, Zone
from app.schemas.reports import STEP_COUNT

DATA_DIR = Path(__file__).resolve().parents[2] / "data"


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Channel(_Strict):
    name: str
    web_url: str
    menu_path: list[str]


class NotReportableCondition(_Strict):
    reason: str
    advice: str


class Eligibility(_Strict):
    reportable_when: list[str]
    not_reportable_when: list[NotReportableCondition]
    basis: str | None = None


class EvidenceSceneDef(_Strict):
    scene_id: str
    label: str
    required: bool
    pass_criteria: str
    retake_tip: str


class CaptureRules(_Strict):
    photo_count_min: int
    interval_seconds: int | None
    same_position_required: bool
    interval_note: str | None = None


class StepAction(_Strict):
    kind: Literal["open_link", "confirm", "save_photos", "copy_text", "submit"]
    button_label: str


class Step(_Strict):
    step_id: str
    order: int
    title: str
    body: str | None = None
    action: StepAction
    reusable: bool
    verified: bool


class InputField(_Strict):
    field_id: str
    label: str
    kind: str


class ZoneDef(_Strict):
    zone_id: Zone
    label: str
    interval_seconds: int
    first_shot_tip: str
    verified: bool


class CaptureGuideTemplate(_Strict):
    title: str
    steps: list[str]
    warning: str


class Procedure(_Strict):
    type_id: TypeId
    label: str
    category: Category
    agency: str | None
    outcome_note: str | None = None
    channel: Channel
    eligibility: Eligibility
    evidence_scenes: list[EvidenceSceneDef]
    capture_rules: CaptureRules
    steps: list[Step]
    input_fields: list[InputField]
    verified: bool
    source_note: str
    # 불법주정차만
    zones: list[ZoneDef] = []
    rehearsal_checks: list[str] = []
    capture_guide: CaptureGuideTemplate | None = None

    def zone(self, zone_id: str | None) -> ZoneDef | None:
        return next((z for z in self.zones if z.zone_id == zone_id), None)

    def scene(self, scene_id: str) -> EvidenceSceneDef | None:
        return next((s for s in self.evidence_scenes if s.scene_id == scene_id), None)


def _check(proc: Procedure, file_name: str) -> None:
    if proc.type_id != file_name:
        raise ValueError(f"{file_name}.json 의 type_id 가 '{proc.type_id}' 예요")
    if [s.order for s in proc.steps] != list(range(1, STEP_COUNT + 1)):
        raise ValueError(f"{file_name}.json 의 steps 는 order 1~{STEP_COUNT} 이어야 해요")
    scene_ids = [s.scene_id for s in proc.evidence_scenes]
    if not scene_ids or len(set(scene_ids)) != len(scene_ids):
        raise ValueError(f"{file_name}.json 의 evidence_scenes 가 비었거나 scene_id 가 겹쳐요")
    if proc.type_id == "illegal_parking" and (not proc.zones or proc.capture_guide is None):
        raise ValueError("illegal_parking.json 에는 zones 와 capture_guide 가 필요해요")


@lru_cache
def _load() -> dict[str, tuple[Procedure, dict[str, Any]]]:
    loaded: dict[str, tuple[Procedure, dict[str, Any]]] = {}
    for type_id in get_args(TypeId):
        path = DATA_DIR / f"{type_id}.json"
        raw = json.loads(path.read_text(encoding="utf-8"))
        proc = Procedure.model_validate(raw)
        _check(proc, type_id)
        loaded[type_id] = (proc, raw)
    return loaded


def load_procedures() -> dict[str, Procedure]:
    return {type_id: pair[0] for type_id, pair in _load().items()}


def get_procedure(type_id: str) -> Procedure:
    return _load()[type_id][0]


def raw_procedure(type_id: str) -> dict[str, Any] | None:
    pair = _load().get(type_id)
    return pair[1] if pair else None


def subtitle(proc: Procedure) -> str:
    """체크박스 아래 한 줄. 예: '구청 청소과 처리 · 안전신문고'."""
    lead = proc.outcome_note or (f"{proc.agency} 처리" if proc.agency else None)
    return " · ".join(part for part in (lead, proc.channel.name) if part)


def interval_label(seconds: int) -> str:
    return f"{seconds // 60}분" if seconds % 60 == 0 else f"{seconds}초"
