# -*- coding: utf-8 -*-
"""气象数据路由：包装 WeatherProcessor.fetch_weather_data"""
import logging
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query

from ..deps import get_weather_processor
from ..schemas.weather import WeatherResponse, WeatherDataItem

router = APIRouter()
logger = logging.getLogger("agri-backend.weather")


@router.get("", response_model=WeatherResponse)
async def get_weather(
    latitude: float = Query(..., description="纬度"),
    longitude: float = Query(..., description="经度"),
    province: str = Query("", description="省份"),
    city: str = Query("", description="城市"),
    hours: int = Query(1, ge=1, le=168, description="未来小时数"),
    wp=Depends(get_weather_processor),
):
    """获取实时气象数据"""
    if not wp:
        return WeatherResponse(
            status=False,
            message="气象 API 未配置，使用默认数据",
            data=[WeatherDataItem(
                timestamp=datetime.now().isoformat(),
                temperature=25.0, humidity=60.0, precipitation=0.0,
                wind_speed=2.0, wind_direction="东北",
            )],
            summary="🌡️ 25.0°C | 💧 湿度60.0% | 🌧️ 降水0.0mm（默认数据）",
            is_mock=True,
        )

    from src.models import Location

    location = Location(province=province, city=city, latitude=latitude, longitude=longitude)
    now = datetime.now()

    try:
        weather_list = await wp.fetch_weather_data(
            location=location,
            start_time=now,
            end_time=now + timedelta(hours=hours),
        )
        if not weather_list:
            return WeatherResponse(status=False, message="未获取到气象数据", is_mock=True)

        items = []
        for w in weather_list:
            items.append(WeatherDataItem(
                timestamp=w.timestamp.isoformat() if hasattr(w.timestamp, "isoformat") else str(w.timestamp),
                temperature=w.temperature,
                max_temperature=getattr(w, "max_temperature", None),
                min_temperature=getattr(w, "min_temperature", None),
                humidity=w.humidity,
                precipitation=w.precipitation,
                wind_speed=w.wind_speed,
                wind_direction=getattr(w, "wind_direction", None),
                sunshine_hours=getattr(w, "sunshine_hours", None),
                pressure=getattr(w, "pressure", None),
            ))

        # 摘要与上方实时指标卡同源：取「当前时次」样本（列表已裁掉早于当前的时次），
        # 降水给的是未来 12h 累计（与指标卡口径一致）。数值统一收敛精度，
        # 避免出现"湿度 45.262604%"这类原始浮点数。
        cur = weather_list[0]
        rain_next12 = sum(
            float(getattr(w, "precipitation", 0) or 0) for w in weather_list[:12]
        )
        summary = (
            f"🌡️ {cur.temperature:.1f}°C | 💧 湿度{cur.humidity:.0f}% | "
            f"🌧️ 未来12h降水{rain_next12:.1f}mm"
        )
        is_mock = getattr(wp, "last_source", "api") == "mock"

        return WeatherResponse(status=True, data=items, summary=summary, is_mock=is_mock)
    except Exception as e:
        logger.error(f"气象数据获取失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"气象数据获取失败: {e}")
