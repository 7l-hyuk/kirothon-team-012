"""절차 데이터로 접수 안내 단계를 조립합니다. 제목과 메뉴 경로는 데이터 그대로이고 AI가 만들지 않습니다."""

from app.schemas.common import PhotoRef
from app.schemas.reports import GuideAction, GuideStep
from app.services.procedures import Procedure


def build_steps(
    proc: Procedure,
    *,
    skip_reusable: bool,
    photos: list[PhotoRef],
    menu_path: list[str],
    address: str | None,
    draft_text: str | None,
) -> list[GuideStep]:
    steps: list[GuideStep] = []
    for step in sorted(proc.steps, key=lambda s: s.order):
        title, body = step.title, step.body
        if "{photo_count}" in title:
            if photos:
                title = title.replace("{photo_count}", str(len(photos)))
            else:
                title = title.replace("아래 {photo_count}장을", "사진을")
        if step.step_id == "select_menu":
            body = " > ".join(menu_path)
        elif step.step_id == "set_location" and address:
            body = address

        action = GuideAction(kind=step.action.kind, button_label=step.action.button_label)
        if step.action.kind == "open_link":
            action.url = proc.channel.web_url
        elif step.action.kind == "save_photos":
            action.photos = photos
        elif step.action.kind == "copy_text":
            action.text = draft_text

        steps.append(
            GuideStep(
                order=step.order,
                step_id=step.step_id,
                title=title,
                body=body,
                action=action,
                skipped=skip_reusable and step.reusable,
                verified=step.verified,
            )
        )
    return steps
