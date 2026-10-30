# -*- coding: utf-8 -*-
"""农场管理路由：包装 farm_core.FarmManager"""
import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException

from ..deps import get_farm_manager, get_weather_processor
from ..schemas.farm import (
    FieldCreate, FieldItem, FieldListResponse,
    FieldActionResponse, FarmAlertsResponse, FarmAlertItem,
)

router = APIRouter()
logger = logging.getLogger("agri-backend.farm")


def _to_item(field) -> FieldItem:
    d = field.to_dict() if hasattr(field, "to_dict") else field.__dict__
    return FieldItem(
        field_id=d.get("field_id", ""),
        name=d.get("name", ""),
        crop=d.get("crop", ""),
        stage=d.get("stage", ""),
        area=d.get("area", 0.0),
        health=d.get("health", 100),
        water=d.get("water", 70),
        growth=d.get("growth", 0),
        is_empty=d.get("is_empty", False),
        actions=d.get("actions", []),
        created_at=str(d["created_at"]) if d.get("created_at") else None,
        planted_at=str(d["planted_at"]) if d.get("planted_at") else None,
        last_updated=str(d["last_updated"]) if d.get("last_updated") else None,
    )


@router.get("/fields", response_model=FieldListResponse)
async def list_fields(manager=Depends(get_farm_manager)):
    fields = manager.list_fields()
    items = [_to_item(f) for f in fields]
    return FieldListResponse(fields=items, total=len(items))


@router.post("/fields", response_model=FieldActionResponse)
async def create_field(req: FieldCreate, manager=Depends(get_farm_manager)):
    try:
        field = manager.create_field(name=req.name, crop=req.crop, stage=req.stage, area=req.area)
        return FieldActionResponse(success=True, message="地块创建成功", field=_to_item(field))
    except Exception as e:
        logger.error(f"创建地块失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/fields/{field_id}", response_model=FieldItem)
async def get_field(field_id: str, manager=Depends(get_farm_manager)):
    field = manager.get_field(field_id)
    if not field:
        raise HTTPException(status_code=404, detail="地块不存在")
    return _to_item(field)


@router.delete("/fields/{field_id}", response_model=FieldActionResponse)
async def delete_field(field_id: str, manager=Depends(get_farm_manager)):
    ok = manager.delete_field(field_id)
    if not ok:
        raise HTTPException(status_code=404, detail="地块不存在")
    return FieldActionResponse(success=True, message="地块已删除")


@router.post("/fields/{field_id}/water", response_model=FieldActionResponse)
async def water_field(field_id: str, manager=Depends(get_farm_manager)):
    ok, msg = manager.water_field(field_id)
    field = manager.get_field(field_id)
    return FieldActionResponse(success=ok, message=msg, field=_to_item(field) if field else None)


@router.post("/fields/{field_id}/fertilize", response_model=FieldActionResponse)
async def fertilize_field(field_id: str, manager=Depends(get_farm_manager)):
    ok, msg = manager.fertilize_field(field_id)
    field = manager.get_field(field_id)
    return FieldActionResponse(success=ok, message=msg, field=_to_item(field) if field else None)


@router.post("/fields/{field_id}/harvest", response_model=FieldActionResponse)
async def harvest_field(field_id: str, manager=Depends(get_farm_manager)):
    ok, msg = manager.harvest_field(field_id)
    field = manager.get_field(field_id)
    return FieldActionResponse(success=ok, message=msg, field=_to_item(field) if field else None)


@router.get("/alerts", response_model=FarmAlertsResponse)
async def get_alerts(
    latitude: float = 34.75,
    longitude: float = 113.65,
    province: str = "",
    city: str = "",
    manager=Depends(get_farm_manager),
    wp=Depends(get_weather_processor),
):
    """地块预警（联动实时气象数据驱动）"""
    weather = {"temperature": 25.0, "humidity": 60.0, "precipitation": 0.0}
    if wp:
        try:
            from datetime import datetime, timedelta
            from src.models import Location

            now = datetime.now()
            loc = Location(province=province, city=city, latitude=latitude, longitude=longitude)
            weather_list = await wp.fetch_weather_data(loc, now, now + timedelta(hours=1))
            if weather_list:
                w = weather_list[0]
                weather = {
                    "temperature": float(w.temperature),
                    "humidity": float(w.humidity),
                    "precipitation": float(w.precipitation),
                }
        except Exception as e:
            logger.warning(f"获取实时气象失败，使用默认值: {e}")

    raw = manager.get_all_alerts(weather)
    alerts = [
        FarmAlertItem(field_name=a.get("field_name", ""), crop=a.get("crop", ""), alerts=a.get("alerts", []))
        for a in raw
    ]
    return FarmAlertsResponse(alerts=alerts)
