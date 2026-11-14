"""여러 응답이 같이 쓰는 값 타입 (명세 1장 '공통 값')."""

from typing import Literal

from pydantic import BaseModel

TypeId = Literal["illegal_parking", "trash_dumping", "illegal_ad", "facility_damage"]
Category = Literal["report", "complaint"]
ReportStatus = Literal["preparing", "filed", "resolved"]
ResultValue = Literal["accepted", "rejected", "unknown"]
ReviewStatus = Literal["sufficient", "insufficient", "undetermined"]
Zone = Literal["fire_hydrant", "intersection_corner", "bus_stop", "crosswalk", "school_zone", "sidewalk"]


class PhotoRef(BaseModel):
    id: str
    url: str


class ScenePhoto(PhotoRef):
    scene_id: str | None = None


class Location(BaseModel):
    address: str | None = None
    district: str | None = None
    dong: str | None = None
