"""고정 응답 데이터. 값은 docs/api-spec.md 예시를 그대로 씁니다."""

from datetime import datetime

from app.schemas.analyses import (
    AnalysisInput,
    AnalysisItem,
    AnalysisResponse,
    NotReportable,
    UnsupportedItem,
)
from app.schemas.common import Location, PhotoRef
from app.schemas.reports import CaptureGuide, RehearsalCheck, RehearsalOut

PLACEHOLDER_URL = "/api/mock/placeholder.svg"
DISCLAIMER = "참고용 안내이며 최종 판단은 담당 기관이 합니다."

MOCK_LOCATION = Location(address="서울시 마포구 ○○로 12", district="마포구", dong="서교동")

# 회색 줄무늬 자리표시 이미지
PLACEHOLDER_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" width="400" height="300" viewBox="0 0 400 300">'
    '<defs><pattern id="s" width="20" height="20" patternUnits="userSpaceOnUse" '
    'patternTransform="rotate(45)"><rect width="10" height="20" fill="#d4d4d8"/>'
    '<rect x="10" width="10" height="20" fill="#e4e4e7"/></pattern></defs>'
    '<rect width="400" height="300" fill="url(#s)"/>'
    '<text x="200" y="156" text-anchor="middle" font-size="16" fill="#52525b" '
    'font-family="sans-serif">예시 사진</text></svg>'
)


def is_not_reportable(text: str | None) -> bool:
    """시나리오 B 조건: 글에 '아파트' 또는 '주차장'이 들어 있으면 신고 불가."""
    return bool(text) and any(word in text for word in ("아파트", "주차장"))


def build_analysis(
    analysis_id: str, created_at: datetime, text: str | None, photos: list[PhotoRef]
) -> AnalysisResponse:
    common = {
        "id": analysis_id,
        "created_at": created_at,
        "input": AnalysisInput(text=text, photos=photos),
        "emergency": False,
        "disclaimer": DISCLAIMER,
    }
    if is_not_reportable(text):  # 시나리오 B
        return AnalysisResponse(
            **common,
            reportable=False,
            summary="아파트 단지 안 주차장으로 보여요. 주민신고로는 접수하기 어려워요.",
            items=[],
            unsupported_items=[],
            not_reportable=NotReportable(
                title="신고가 어려운 상황이에요",
                message="아파트 단지 안 주차장은 사유지라 주민신고 대상이 아니에요. 관리사무소에 문의해 보세요.",
                basis="주민신고는 도로 위 6대 금지구역(소화전, 교차로 모퉁이, 버스정류소, 횡단보도, 어린이보호구역, 인도)에만 적용돼요.",
            ),
            location=Location(),
        )
    return AnalysisResponse(  # 시나리오 A
        **common,
        reportable=True,
        summary="인도 위에 주차된 차량 1대와, 전봇대 아래 무단투기된 쓰레기가 보여요. 아래 2건을 신고할 수 있어요.",
        items=[
            AnalysisItem(
                type_id="illegal_parking",
                category="report",
                label="불법주정차 (인도)",
                subtitle="과태료 부과 대상 · 안전신문고",
                reason="인도는 6대 주정차 금지구역이라 주민 신고만으로 과태료가 부과돼요.",
                detail={"zone": "sidewalk"},
            ),
            AnalysisItem(
                type_id="trash_dumping",
                category="complaint",
                label="쓰레기 무단투기",
                subtitle="구청 청소과 처리 · 안전신문고",
                reason="공공장소에 종량제 봉투 없이 버려진 생활쓰레기는 무단투기 신고 대상이에요.",
                detail={},
            ),
        ],
        unsupported_items=[UnsupportedItem(label="전봇대 낙서", message="아직 안내하지 못하는 유형이에요")],
        not_reportable=None,
        location=MOCK_LOCATION,
    )


def build_rehearsal(zone: str) -> RehearsalOut:
    return RehearsalOut(
        passed=False,
        zone=zone,
        checks=[
            RehearsalCheck(key="zone", status="sufficient", label="금지구역: 인도 위 주차", detail=None),
            RehearsalCheck(key="plate_readable", status="sufficient", label="번호판이 식별돼요", detail=None),
            RehearsalCheck(
                key="background_included",
                status="insufficient",
                label="주변 배경이 부족해요",
                detail="차량만 크게 찍혔어요. 인도 경계석과 옆 건물이 함께 보이게 찍어야 해요.",
            ),
        ],
        capture_guide=CaptureGuide(
            title="안전신문고 앱에서 이렇게 찍으세요",
            steps=[
                "차량 뒤쪽에서 번호판과 인도 경계석이 함께 나오게 1장",
                "그 자리에서 움직이지 말고 1분 기다리기",
                "같은 위치, 같은 방향으로 1장 더",
            ],
            warning="앞에서 1장, 옆에서 1장은 반려돼요.",
            interval_seconds=60,
            interval_note="어린이보호구역은 5분 간격이 필요할 수 있어요",
        ),
    )


# 문구 대필: (type_id, tone) → 고정 문구. 첫 문구는 명세 예시를 그대로 씁니다.
DRAFTS: dict[tuple[str, str], str] = {
    ("trash_dumping", "default"): (
        "서울시 마포구 ○○로 12 앞 전봇대 아래에 종량제 봉투를 쓰지 않은 생활쓰레기가 무단투기되어 있습니다. "
        "2026년 11월 14일 오후 2시경 확인했으며, 악취와 통행 불편이 있어 수거와 단속을 요청드립니다."
    ),
    ("trash_dumping", "shorter"): "서울시 마포구 ○○로 12 앞 전봇대 아래에 생활쓰레기가 무단투기되어 있습니다. 수거와 단속을 요청합니다.",
    ("trash_dumping", "politer"): (
        "안녕하세요. 서울시 마포구 ○○로 12 앞 전봇대 아래에 종량제 봉투 없이 버려진 생활쓰레기가 있어 신고드립니다. "
        "악취와 통행 불편이 있으니 바쁘시겠지만 수거와 단속을 부탁드립니다. 감사합니다."
    ),
    ("illegal_parking", "default"): (
        "서울시 마포구 ○○로 12 앞 인도 위에 차량이 주정차되어 있어 보행자가 차도로 내려가야 합니다. "
        "2026년 11월 14일 오후 2시경 같은 위치에서 1분 간격으로 촬영했으며, 확인 후 조치를 요청드립니다."
    ),
    ("illegal_parking", "shorter"): "서울시 마포구 ○○로 12 앞 인도 위에 차량이 주정차되어 있습니다. 같은 위치에서 1분 간격으로 촬영했습니다.",
    ("illegal_parking", "politer"): (
        "안녕하세요. 서울시 마포구 ○○로 12 앞 인도 위에 차량이 주정차되어 보행자가 불편을 겪고 있어 신고드립니다. "
        "같은 위치에서 1분 간격으로 촬영한 사진을 첨부했으니 확인해 주시면 감사하겠습니다."
    ),
}
