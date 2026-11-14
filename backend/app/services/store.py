"""DB 저장소: 분석, 신고 건, 증거 장면 상태, 사진 행의 읽기와 쓰기.

세션은 요청 단위로 라우터가 열어 넘겨 줍니다. 모든 조회에 device_id 조건을 겁니다(다른 기기의 리소스는 없는 것과 같습니다).
사진 URL은 저장하지 않고, 응답을 만들 때 `photo_url()`로 만듭니다.
"""

from dataclasses import asdict, dataclass, field
from uuid import uuid4

from sqlalchemy import func
from sqlmodel import Session, select

from app.mock.fixtures import PLACEHOLDER_URL
from app.models import Analysis, Photo, Report
from app.schemas.analyses import AnalysisInput, AnalysisResponse
from app.schemas.common import PhotoRef, ScenePhoto
from app.schemas.reports import SceneReview
from app.storage import get_storage
from app.timeutil import now_kst


# ---------------------------------------------------------------- 사진
def photo_key(photo_id: str, when=None) -> str:
    """저장소 키: photos/{yyyy}/{mm}/{photo_id}.jpg (KST 기준 연·월). 사용자 입력 파일명은 쓰지 않습니다."""
    when = when or now_kst()
    return f"photos/{when.year:04d}/{when.month:02d}/{photo_id}.jpg"


def photo_url(photo: Photo) -> str:
    if photo.s3_key is None:  # 가짜 모드의 자리표시 사진
        return PLACEHOLDER_URL
    return get_storage().url(photo.s3_key, photo.id)


def photo_ref(photo: Photo) -> PhotoRef:
    return PhotoRef(id=photo.id, url=photo_url(photo))


def new_photo(
    device_id: str,
    jpeg: bytes | None,
    *,
    analysis_id: str | None = None,
    report_id: str | None = None,
    scene_id: str | None = None,
    review: SceneReview | None = None,
    order: int = 1,
) -> Photo:
    """사진 행을 만들고 바이트를 저장소에 올립니다. 행은 세션에 아직 넣지 않습니다(부모를 먼저 flush하기 위해서).

    `jpeg`가 None이면 파일 없는 자리표시 사진입니다(가짜 모드).
    """
    photo_id = str(uuid4())
    now = now_kst()
    key = None
    if jpeg is not None:
        key = photo_key(photo_id, now)
        get_storage().put(key, jpeg)
    return Photo(
        id=photo_id,
        device_id=device_id,
        analysis_id=analysis_id,
        report_id=report_id,
        s3_key=key,
        scene_id=scene_id,
        review_status=review.status if review else None,
        review_message=review.message if review else None,
        retake_tip=review.retake_tip if review else None,
        taken_order=order,
        created_at=now,
    )


def get_photo(session: Session, photo_id: str) -> Photo | None:
    return session.get(Photo, photo_id)


def read_photo_bytes(photo: Photo) -> bytes:
    """저장소에서 사진 바이트를 다시 읽습니다(사전 점검이 분석 때 올린 사진을 다시 쓸 때)."""
    assert photo.s3_key is not None
    return get_storage().get(photo.s3_key)


def photo_refs(session: Session, ids: list[str]) -> dict[str, PhotoRef]:
    if not ids:
        return {}
    rows = session.exec(select(Photo).where(Photo.id.in_(list(set(ids))))).all()  # type: ignore[attr-defined]
    return {p.id: photo_ref(p) for p in rows}


def next_photo_order(session: Session, report_id: str) -> int:
    count = session.exec(select(func.count()).select_from(Photo).where(Photo.report_id == report_id)).one()
    return count + 1


# ---------------------------------------------------------------- 분석
@dataclass
class SceneMatch:
    """분석 때 올린 사진이 이미 충족한 증거 장면. 신고 건을 만들 때 AI 재호출 없이 반영합니다."""

    scene_id: str
    photo_id: str
    message: str


@dataclass
class AnalysisRecord:
    id: str
    device_id: str
    response: AnalysisResponse
    scene_matches: dict[str, list[SceneMatch]] = field(default_factory=dict)  # type_id → 장면 목록
    item_photo_ids: dict[str, list[str]] = field(default_factory=dict)  # type_id → 그 문제가 보이는 사진 ID(번호순)


def save_analysis(
    session: Session,
    device_id: str,
    response: AnalysisResponse,
    scene_matches: dict[str, list[SceneMatch]],
    item_photo_ids: dict[str, list[str]],
    photos: list[Photo],
) -> None:
    """분석과 그 사진 행을 한 트랜잭션으로 저장합니다. 부모(분석)를 먼저 flush합니다."""
    session.add(
        Analysis(
            id=response.id,
            device_id=device_id,
            situation_text=response.input.text,
            result=response.model_dump(mode="json", exclude={"id", "created_at", "input"}),
            scene_matches={t: [asdict(m) for m in ms] for t, ms in scene_matches.items()},
            item_photo_ids=item_photo_ids,
            address=response.location.address,
            district=response.location.district,
            dong=response.location.dong,
            created_at=response.created_at,
        )
    )
    session.flush()
    session.add_all(photos)
    session.commit()


def load_analysis(session: Session, device_id: str, analysis_id: str) -> AnalysisRecord | None:
    row = session.exec(
        select(Analysis).where(Analysis.id == analysis_id, Analysis.device_id == device_id)
    ).first()
    if row is None:
        return None
    photos = session.exec(
        select(Photo).where(Photo.analysis_id == row.id).order_by(Photo.taken_order, Photo.created_at)  # type: ignore[arg-type]
    ).all()
    response = AnalysisResponse(
        id=row.id,
        created_at=row.created_at,
        input=AnalysisInput(text=row.situation_text, photos=[photo_ref(p) for p in photos]),
        **row.result,
    )
    return AnalysisRecord(
        id=row.id,
        device_id=row.device_id,
        response=response,
        scene_matches={t: [SceneMatch(**m) for m in ms] for t, ms in row.scene_matches.items()},
        item_photo_ids={t: list(ids) for t, ids in row.item_photo_ids.items()},
    )


# ---------------------------------------------------------------- 신고 건
@dataclass
class SceneState:
    photo_id: str | None = None
    review: SceneReview | None = None
    attempts: int = 0  # 가짜 모드에서만 씀. 1회차 불충분, 2회차부터 충분


def get_report(session: Session, device_id: str, report_id: str) -> Report | None:
    return session.exec(select(Report).where(Report.id == report_id, Report.device_id == device_id)).first()


def reports_exist_for_analysis(session: Session, device_id: str, analysis_id: str) -> bool:
    row = session.exec(
        select(Report.id).where(Report.analysis_id == analysis_id, Report.device_id == device_id).limit(1)
    ).first()
    return row is not None


def scene_state(rec: Report, scene_id: str) -> SceneState:
    raw = (rec.scenes or {}).get(scene_id)
    if not raw:
        return SceneState()
    review = raw.get("review")
    return SceneState(
        photo_id=raw.get("photo_id"),
        review=SceneReview(**review) if review else None,
        attempts=raw.get("attempts", 0),
    )


def set_scene(rec: Report, scene_id: str, state: SceneState) -> None:
    """장면 상태를 바꿉니다. JSON 컬럼은 새 dict를 대입해야 변경이 감지됩니다."""
    scenes = dict(rec.scenes or {})
    scenes[scene_id] = {
        "photo_id": state.photo_id,
        "review": state.review.model_dump() if state.review else None,
        "attempts": state.attempts,
    }
    rec.scenes = scenes


# 사전 점검 항목별 판정은 새 컬럼 없이 reports.scenes(JSON)의 예약 키에 둡니다. 장면 id와 겹치지 않습니다.
REHEARSAL_KEY = "_rehearsal"
REHEARSAL_SCENE_MESSAGE = "사전 점검을 마쳤어요"  # 사전 점검이 증거 장면을 채울 때 넣는 문구(사진 검수 결과가 아님)


def set_rehearsal_checks(rec: Report, checks: list[tuple[str, str]]) -> None:
    scenes = dict(rec.scenes or {})
    scenes[REHEARSAL_KEY] = {"checks": [{"key": k, "status": s} for k, s in checks]}
    rec.scenes = scenes


def rehearsal_checks(rec: Report) -> list[tuple[str, str]]:
    raw = (rec.scenes or {}).get(REHEARSAL_KEY) or {}
    return [(c["key"], c["status"]) for c in raw.get("checks", [])]


def scene_refs(session: Session, rec: Report) -> dict[str, PhotoRef]:
    """사진이 있는 장면의 scene_id → 사진(URL 포함)."""
    ids = {sid: st.photo_id for sid in (rec.scenes or {}) if (st := scene_state(rec, sid)).photo_id}
    refs = photo_refs(session, list(ids.values()))
    return {sid: refs[pid] for sid, pid in ids.items() if pid in refs}


def report_photos(session: Session, rec: Report) -> list[ScenePhoto]:
    """이 건의 사진: 장면에 쓰는 사진 + 장면 없이 올린 사진. 대체된 이전 사진은 들어가지 않습니다."""
    refs = scene_refs(session, rec)
    photos = [ScenePhoto(id=r.id, url=r.url, scene_id=sid) for sid, r in refs.items()]
    extras = session.exec(
        select(Photo)
        .where(Photo.report_id == rec.id, Photo.scene_id.is_(None))  # type: ignore[union-attr]
        .order_by(Photo.taken_order, Photo.created_at)  # type: ignore[arg-type]
    ).all()
    return photos + [ScenePhoto(id=p.id, url=photo_url(p), scene_id=None) for p in extras]
