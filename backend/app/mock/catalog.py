"""유형별 고정 정보 (라벨, 메뉴 경로, 증거 장면). 값은 docs/api-spec.md 예시를 따릅니다.
진짜 절차 데이터는 backend/data/*.json 으로 옮길 예정이며, 여기 값은 모두 [확인 필요]입니다."""

from dataclasses import dataclass

WEB_URL = "https://www.safetyreport.go.kr"
CHANNEL_NAME = "안전신문고"


@dataclass(frozen=True)
class SceneDef:
    scene_id: str
    label: str
    sufficient_message: str
    insufficient_message: str
    retake_tip: str
    prefill_from_analysis: bool = False  # 분석 때 올린 사진으로 처음부터 충족


@dataclass(frozen=True)
class TypeDef:
    type_id: str
    menu_path: tuple[str, ...]
    capture_in_app: bool
    scenes: tuple[SceneDef, ...]


CATALOG: dict[str, TypeDef] = {
    "trash_dumping": TypeDef(
        type_id="trash_dumping",
        menu_path=("생활불편 신고", "쓰레기·폐기물"),
        capture_in_app=True,
        scenes=(
            SceneDef(
                scene_id="overview",
                label="쓰레기 전체가 보이는 사진",
                sufficient_message="올리신 사진으로 충분해요",
                insufficient_message="쓰레기가 일부 잘려서 전체 양을 알기 어려워요.",
                retake_tip="쓰레기가 잘리지 않게 한두 걸음 물러나 주세요.",
                prefill_from_analysis=True,
            ),
            SceneDef(
                scene_id="location",
                label="주변 건물이나 도로명이 보이는 사진",
                sufficient_message="건물 간판과 도로명이 보여서 위치를 알 수 있어요.",
                insufficient_message="도로명 표지판이 잘려서 위치를 알기 어려워요.",
                retake_tip="두세 걸음 뒤로 물러나서 건물 간판이 함께 나오게 다시 찍어 주세요.",
            ),
        ),
    ),
    "illegal_parking": TypeDef(
        type_id="illegal_parking",
        menu_path=("불법 주정차 신고", "인도"),
        capture_in_app=False,
        # 본촬영은 안전신문고 앱에서 하므로 사전 점검(rehearsals)을 마치면 충족 처리합니다.
        scenes=(
            SceneDef(
                scene_id="vehicle",
                label="번호판과 주변 배경이 보이는 사진",
                sufficient_message="사전 점검을 마쳤어요",
                insufficient_message="번호판이나 주변 배경이 잘 안 보여요.",
                retake_tip="차량 뒤쪽에서 번호판과 인도 경계석이 함께 나오게 찍어 주세요.",
            ),
        ),
    ),
}
