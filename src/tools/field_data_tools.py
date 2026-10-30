# -*- coding: utf-8 -*-
"""
田间数据闭环工具集
实现地块档案、农事日志、传感器接口
"""
from typing import Dict, List, Optional, Any
from datetime import datetime, date
from src.models import (
    FieldInfo, FieldRecord, RecordType,
    SensorData, SensorType, Location
)


class FieldManagementTool:
    """地块档案管理工具"""
    
    def __init__(self):
        self.name = "field_management"
        self.description = "多地块档案管理"
        self.fields: Dict[str, FieldInfo] = {}
    
    def create_field(
        self,
        field_id: str,
        location: Location,
        area: float,
        soil_type: str,
        crop_type: str,
        variety: Optional[str] = None,
        sowing_date: Optional[date] = None,
        irrigation_system: Optional[str] = None
    ) -> FieldInfo:
        """
        创建地块档案
        
        Args:
            field_id: 地块ID
            location: 地理位置
            area: 面积（亩）
            soil_type: 土壤类型
            crop_type: 作物类型
            variety: 品种
            sowing_date: 播种日期
            irrigation_system: 灌溉系统
        
        Returns:
            地块信息
        """
        from src.models import CropType
        
        crop_enum = CropType(crop_type) if isinstance(crop_type, str) else crop_type
        
        field = FieldInfo(
            field_id=field_id,
            location=location,
            area=area,
            soil_type=soil_type,
            crop_type=crop_enum,
            variety=variety,
            sowing_date=sowing_date,
            irrigation_system=irrigation_system
        )
        
        self.fields[field_id] = field
        
        return field
    
    def get_field(self, field_id: str) -> Optional[FieldInfo]:
        """获取地块信息"""
        return self.fields.get(field_id)
    
    def list_fields(self) -> List[FieldInfo]:
        """列出所有地块"""
        return list(self.fields.values())
    
    def update_field(
        self,
        field_id: str,
        **kwargs
    ) -> Optional[FieldInfo]:
        """更新地块信息"""
        field = self.fields.get(field_id)
        if not field:
            return None
        
        for key, value in kwargs.items():
            if hasattr(field, key):
                setattr(field, key, value)
        
        return field
    
    def delete_field(self, field_id: str) -> bool:
        """删除地块"""
        if field_id in self.fields:
            del self.fields[field_id]
            return True
        return False


class FieldRecordTool:
    """田间记录/农事日志工具"""
    
    def __init__(self):
        self.name = "field_record"
        self.description = "农事日志记录与管理"
        self.records: Dict[str, FieldRecord] = {}
    
    def add_record(
        self,
        record_id: str,
        field_id: str,
        record_type: str,
        record_date: date,
        operation_details: str,
        inputs_used: Optional[Dict[str, float]] = None,
        cost: Optional[float] = None,
        weather_condition: Optional[str] = None,
        notes: Optional[str] = None
    ) -> FieldRecord:
        """
        添加农事记录
        
        Args:
            record_id: 记录ID
            field_id: 地块ID
            record_type: 记录类型
            record_date: 记录日期
            operation_details: 操作详情
            inputs_used: 投入品及用量
            cost: 成本
            weather_condition: 天气条件
            notes: 备注
        
        Returns:
            农事记录
        """
        record = FieldRecord(
            record_id=record_id,
            field_id=field_id,
            record_type=RecordType(record_type),
            record_date=record_date,
            operation_details=operation_details,
            inputs_used=inputs_used,
            cost=cost,
            weather_condition=weather_condition,
            notes=notes
        )
        
        self.records[record_id] = record
        
        return record
    
    def get_records_by_field(
        self,
        field_id: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> List[FieldRecord]:
        """
        获取地块的农事记录
        
        Args:
            field_id: 地块ID
            start_date: 开始日期
            end_date: 结束日期
        
        Returns:
            农事记录列表
        """
        records = [r for r in self.records.values() if r.field_id == field_id]
        
        if start_date:
            records = [r for r in records if r.record_date >= start_date]
        
        if end_date:
            records = [r for r in records if r.record_date <= end_date]
        
        return sorted(records, key=lambda x: x.record_date, reverse=True)
    
    def analyze_records(
        self,
        field_id: str,
        period_days: int = 30
    ) -> Dict[str, Any]:
        """
        分析农事记录
        
        Args:
            field_id: 地块ID
            period_days: 分析周期（天）
        
        Returns:
            分析结果
        """
        end_date = date.today()
        start_date = end_date - __import__('datetime').timedelta(days=period_days)
        
        records = self.get_records_by_field(field_id, start_date, end_date)
        
        total_cost = sum(r.cost for r in records if r.cost)
        
        operation_counts = {}
        for record in records:
            op_type = record.record_type.value
            operation_counts[op_type] = operation_counts.get(op_type, 0) + 1
        
        return {
            "period": f"{start_date} ~ {end_date}",
            "total_records": len(records),
            "total_cost": total_cost,
            "operation_counts": operation_counts,
            "average_cost_per_day": total_cost / period_days if period_days > 0 else 0
        }


class SensorDataTool:
    """传感器数据接口工具"""
    
    def __init__(self):
        self.name = "sensor_data"
        self.description = "田间传感器数据接入"
        self.sensor_data: Dict[str, List[SensorData]] = {}
    
    def receive_sensor_data(
        self,
        sensor_id: str,
        sensor_type: str,
        field_id: str,
        value: float,
        unit: str,
        timestamp: Optional[datetime] = None,
        location_description: Optional[str] = None
    ) -> SensorData:
        """
        接收传感器数据
        
        Args:
            sensor_id: 传感器ID
            sensor_type: 传感器类型
            field_id: 地块ID
            value: 数值
            unit: 单位
            timestamp: 时间戳
            location_description: 位置描述
        
        Returns:
            传感器数据
        """
        data = SensorData(
            sensor_id=sensor_id,
            sensor_type=SensorType(sensor_type),
            field_id=field_id,
            value=value,
            unit=unit,
            timestamp=timestamp or datetime.now(),
            location_description=location_description
        )
        
        if sensor_id not in self.sensor_data:
            self.sensor_data[sensor_id] = []
        
        self.sensor_data[sensor_id].append(data)
        
        return data
    
    def get_latest_data(
        self,
        field_id: str,
        sensor_type: Optional[str] = None
    ) -> Dict[str, SensorData]:
        """
        获取最新传感器数据
        
        Args:
            field_id: 地块ID
            sensor_type: 传感器类型
        
        Returns:
            最新传感器数据字典
        """
        latest_data = {}
        
        for sensor_id, data_list in self.sensor_data.items():
            for data in data_list:
                if data.field_id == field_id:
                    if sensor_type and data.sensor_type.value != sensor_type:
                        continue
                    
                    key = f"{sensor_id}_{data.sensor_type.value}"
                    if key not in latest_data or data.timestamp > latest_data[key].timestamp:
                        latest_data[key] = data
        
        return latest_data
    
    def detect_anomaly(
        self,
        sensor_data: SensorData,
        threshold_low: Optional[float] = None,
        threshold_high: Optional[float] = None
    ) -> bool:
        """
        检测异常数据
        
        Args:
            sensor_data: 传感器数据
            threshold_low: 下限阈值
            threshold_high: 上限阈值
        
        Returns:
            是否异常
        """
        default_thresholds = {
            SensorType.SOIL_TEMPERATURE: (5, 40),
            SensorType.SOIL_MOISTURE: (20, 90),
            SensorType.AIR_TEMPERATURE: (-10, 45),
            SensorType.AIR_HUMIDITY: (20, 100),
            SensorType.LIGHT_INTENSITY: (0, 100000),
            SensorType.CO2_CONCENTRATION: (300, 2000)
        }
        
        if threshold_low is None or threshold_high is None:
            thresholds = default_thresholds.get(sensor_data.sensor_type, (None, None))
            threshold_low = threshold_low or thresholds[0]
            threshold_high = threshold_high or thresholds[1]
        
        if threshold_low is not None and sensor_data.value < threshold_low:
            sensor_data.is_anomaly = True
            sensor_data.anomaly_reason = f"数值{sensor_data.value}低于下限{threshold_low}"
            return True
        
        if threshold_high is not None and sensor_data.value > threshold_high:
            sensor_data.is_anomaly = True
            sensor_data.anomaly_reason = f"数值{sensor_data.value}超过上限{threshold_high}"
            return True
        
        return False

