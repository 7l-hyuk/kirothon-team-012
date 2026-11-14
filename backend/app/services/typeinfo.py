"""유형 정보 조회. 가짜 모드는 mock 카탈로그, 실제 모드는 절차 데이터(backend/data)를 씁니다."""

from app.config import is_mock
from app.mock.catalog import CATALOG, CHANNEL_NAME, WEB_URL, SceneDef, TypeDef
from app.services import procedures


def _from_procedure(proc: procedures.Procedure) -> TypeDef:
    return TypeDef(
        type_id=proc.type_id,
        menu_path=tuple(proc.channel.menu_path),
        capture_in_app=not proc.capture_rules.same_position_required,  # 같은 자리 촬영은 안전신문고 앱에서
        scenes=tuple(
            SceneDef(
                scene_id=s.scene_id,
                label=s.label,
                sufficient_message="이 사진으로 충분해요",
                insufficient_message="",
                retake_tip=s.retake_tip,
                required=s.required,
            )
            for s in proc.evidence_scenes
        ),
    )


def type_def(type_id: str) -> TypeDef:
    if is_mock():
        return CATALOG[type_id]
    return _from_procedure(procedures.get_procedure(type_id))


def channel_info(type_id: str, zone: str | None) -> tuple[str, str, list[str]]:
    """(접수처 이름, 웹 주소, 메뉴 경로). 불법주정차는 구역이 알려져 있으면 메뉴 끝에 붙입니다."""
    if is_mock():
        return CHANNEL_NAME, WEB_URL, list(CATALOG[type_id].menu_path)
    proc = procedures.get_procedure(type_id)
    menu = list(proc.channel.menu_path)
    zone_def = proc.zone(zone)
    if zone_def:
        menu.append(zone_def.label)
    return proc.channel.name, proc.channel.web_url, menu
