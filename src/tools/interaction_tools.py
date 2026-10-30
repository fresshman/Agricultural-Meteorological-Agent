# -*- coding: utf-8 -*-
"""
工具交互服务工具集
实现任务推送、图像识别接口、历史复盘
"""
from typing import Dict, List, Optional, Any
from datetime import datetime, date, timedelta
from src.models import (
    TaskReminder, TaskType, RiskLevel,
    ImageRecognitionResult, HistoricalReview,
    CropType
)


class TaskReminderTool:
    """农事任务推送工具"""
    
    def __init__(self):
        self.name = "task_reminder"
        self.description = "农事任务主动推送与提醒"
        self.tasks: Dict[str, TaskReminder] = {}
    
    def create_reminder(
        self,
        task_id: str,
        task_type: str,
        field_id: str,
        scheduled_time: datetime,
        task_description: str,
        priority: str = "中风险",
        weather_condition: Optional[str] = None,
        notes: Optional[str] = None
    ) -> TaskReminder:
        """
        创建任务提醒
        
        Args:
            task_id: 任务ID
            task_type: 任务类型
            field_id: 地块ID
            scheduled_time: 计划时间
            task_description: 任务描述
            priority: 优先级
            weather_condition: 天气条件
            notes: 备注
        
        Returns:
            任务提醒
        """
        task = TaskReminder(
            task_id=task_id,
            task_type=TaskType(task_type),
            field_id=field_id,
            scheduled_time=scheduled_time,
            task_description=task_description,
            priority=RiskLevel(priority),
            weather_condition=weather_condition,
            notes=notes
        )
        
        self.tasks[task_id] = task
        
        return task
    
    def get_upcoming_tasks(
        self,
        field_id: Optional[str] = None,
        days: int = 7
    ) -> List[TaskReminder]:
        """
        获取即将到来的任务
        
        Args:
            field_id: 地块ID（可选）
            days: 未来天数
        
        Returns:
            任务列表
        """
        now = datetime.now()
        end_time = now + timedelta(days=days)
        
        tasks = [
            task for task in self.tasks.values()
            if not task.is_completed
            and now <= task.scheduled_time <= end_time
        ]
        
        if field_id:
            tasks = [t for t in tasks if t.field_id == field_id]
        
        return sorted(tasks, key=lambda x: x.scheduled_time)
    
    def complete_task(self, task_id: str) -> bool:
        """完成任务"""
        task = self.tasks.get(task_id)
        if task:
            task.is_completed = True
            task.completed_time = datetime.now()
            return True
        return False
    
    def generate_smart_reminders(
        self,
        weather_forecast: List[Dict[str, Any]],
        crop_type: CropType,
        field_id: str
    ) -> List[TaskReminder]:
        """
        智能生成提醒
        
        Args:
            weather_forecast: 天气预报
            crop_type: 作物类型
            field_id: 地块ID
        
        Returns:
            智能提醒列表
        """
        reminders = []
        now = datetime.now()
        
        for i, weather in enumerate(weather_forecast[:7]):
            forecast_time = now + timedelta(days=i)
            
            if weather.get("precipitation", 0) < 0.5 and weather.get("wind_speed", 0) < 3:
                task_id = f"auto_spray_{field_id}_{i}"
                reminder = self.create_reminder(
                    task_id=task_id,
                    task_type="喷药提醒",
                    field_id=field_id,
                    scheduled_time=forecast_time.replace(hour=9, minute=0),
                    task_description=f"适宜喷药时段：{forecast_time.strftime('%m月%d日')}上午",
                    priority="中风险",
                    weather_condition=f"无雨，风速{weather.get('wind_speed', 0):.1f}m/s"
                )
                reminders.append(reminder)
            
            if weather.get("min_temp", 20) < 5:
                task_id = f"auto_frost_{field_id}_{i}"
                reminder = self.create_reminder(
                    task_id=task_id,
                    task_type="霜冻预警",
                    field_id=field_id,
                    scheduled_time=forecast_time.replace(hour=5, minute=0),
                    task_description=f"霜冻预警：{forecast_time.strftime('%m月%d日')}凌晨最低温{weather.get('min_temp', 0):.1f}°C",
                    priority="高风险",
                    weather_condition=f"最低温度{weather.get('min_temp', 0):.1f}°C"
                )
                reminders.append(reminder)
        
        return reminders


class ImageRecognitionTool:
    """图像识别联动工具"""
    
    def __init__(self):
        self.name = "image_recognition"
        self.description = "作物病虫草害图像识别"
        
        self.disease_database = {
            "霜霉病": {
                "symptoms": ["叶片背面白色霉层", "叶片正面黄色斑点", "病斑受叶脉限制"],
                "weather_correlation": "高湿、结露时间长易发",
                "control": ["甲霜灵·锰锌", "霜脲·锰锌", "烯酰吗啉"]
            },
            "白粉病": {
                "symptoms": ["叶片正面白色粉状物", "病斑连片", "后期变黑"],
                "weather_correlation": "中等湿度、昼夜温差大易发",
                "control": ["三唑酮", "腈菌唑", "苯醚甲环唑"]
            },
            "蚜虫": {
                "symptoms": ["叶片卷曲", "嫩梢有虫体", "蜜露"],
                "weather_correlation": "温度适宜、湿度适中易发",
                "control": ["吡虫啉", "啶虫脒", "噻虫嗪"]
            }
        }
    
    def recognize_image(
        self,
        image_id: str,
        recognition_type: str,
        detected_object: str,
        confidence: float,
        severity: Optional[str] = None
    ) -> ImageRecognitionResult:
        """
        识别图像
        
        Args:
            image_id: 图像ID
            recognition_type: 识别类型
            detected_object: 检测对象
            confidence: 置信度
            severity: 严重程度
        
        Returns:
            识别结果
        """
        weather_correlation = None
        control_recommendation = "请咨询当地农技部门"
        chemical_options = []
        prevention_measures = []
        
        if detected_object in self.disease_database:
            disease_info = self.disease_database[detected_object]
            weather_correlation = disease_info["weather_correlation"]
            chemical_options = disease_info["control"]
            control_recommendation = f"建议使用{chemical_options[0]}等药剂防治"
            prevention_measures = [
                "加强田间管理",
                "改善通风透光",
                "及时清除病株残体"
            ]
        
        return ImageRecognitionResult(
            image_id=image_id,
            recognition_type=recognition_type,
            detected_object=detected_object,
            confidence=confidence,
            severity=severity,
            weather_correlation=weather_correlation,
            control_recommendation=control_recommendation,
            chemical_options=chemical_options,
            prevention_measures=prevention_measures
        )
    
    def analyze_with_weather(
        self,
        recognition_result: ImageRecognitionResult,
        recent_weather: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        结合气象分析识别结果
        
        Args:
            recognition_result: 识别结果
            recent_weather: 近期气象数据
        
        Returns:
            综合分析结果
        """
        analysis = {
            "disease": recognition_result.detected_object,
            "weather_factors": [],
            "cause_analysis": "",
            "recommendation": ""
        }
        
        if not recent_weather:
            return analysis
        
        avg_humidity = sum(w.get("humidity", 60) for w in recent_weather) / len(recent_weather)
        avg_temp = sum(w.get("temperature", 20) for w in recent_weather) / len(recent_weather)
        
        if avg_humidity > 80:
            analysis["weather_factors"].append(f"近期平均湿度{avg_humidity:.1f}%，偏高")
        
        if avg_temp > 25:
            analysis["weather_factors"].append(f"近期平均温度{avg_temp:.1f}°C，适宜病害发展")
        
        if recognition_result.weather_correlation:
            analysis["cause_analysis"] = f"气象条件分析：{recognition_result.weather_correlation}"
        
        analysis["recommendation"] = recognition_result.control_recommendation
        
        return analysis


class HistoricalReviewTool:
    """历史气象复盘工具"""
    
    def __init__(self):
        self.name = "historical_review"
        self.description = "历史气象复盘与农事总结"
        self.reviews: Dict[str, HistoricalReview] = {}
    
    def create_review(
        self,
        field_id: str,
        start_date: date,
        end_date: date,
        review_type: str,
        weather_data: List[Dict[str, Any]],
        operation_records: List[Dict[str, Any]]
    ) -> HistoricalReview:
        """
        创建历史复盘
        
        Args:
            field_id: 地块ID
            start_date: 开始日期
            end_date: 结束日期
            review_type: 复盘类型
            weather_data: 气象数据
            operation_records: 农事记录
        
        Returns:
            历史复盘
        """
        review_id = f"review_{field_id}_{start_date}_{end_date}"
        
        weather_summary, weather_anomalies = self._analyze_weather(weather_data)
        
        operation_summary, successful_ops, failed_ops = self._analyze_operations(operation_records)
        
        lessons_learned = self._extract_lessons(weather_anomalies, operation_records)
        
        recommendations = self._generate_future_recommendations(lessons_learned)
        
        review = HistoricalReview(
            review_id=review_id,
            field_id=field_id,
            review_period=(start_date, end_date),
            review_type=review_type,
            weather_summary=weather_summary,
            weather_anomalies=weather_anomalies,
            operation_summary=operation_summary,
            successful_operations=successful_ops,
            failed_operations=failed_ops,
            lessons_learned=lessons_learned,
            recommendations=recommendations
        )
        
        self.reviews[review_id] = review
        
        return review
    
    def _analyze_weather(
        self,
        weather_data: List[Dict[str, Any]]
    ) -> Tuple[str, List[str]]:
        """分析气象数据"""
        if not weather_data:
            return "无气象数据", []
        
        temps = [w.get("temperature", 20) for w in weather_data]
        precips = [w.get("precipitation", 0) for w in weather_data]
        
        avg_temp = sum(temps) / len(temps)
        total_precip = sum(precips)
        
        summary = f"平均温度{avg_temp:.1f}°C，累计降水{total_precip:.1f}mm"
        
        anomalies = []
        if min(temps) < 0:
            anomalies.append(f"最低温度{min(temps):.1f}°C，出现霜冻")
        if max(temps) > 35:
            anomalies.append(f"最高温度{max(temps):.1f}°C，出现高温")
        if total_precip > 200:
            anomalies.append(f"累计降水{total_precip:.1f}mm，偏多")
        elif total_precip < 50:
            anomalies.append(f"累计降水{total_precip:.1f}mm，偏少")
        
        return summary, anomalies
    
    def _analyze_operations(
        self,
        operation_records: List[Dict[str, Any]]
    ) -> Tuple[str, List[str], List[str]]:
        """分析农事记录"""
        if not operation_records:
            return "无农事记录", [], []
        
        summary = f"共{len(operation_records)}次农事操作"
        
        successful = []
        failed = []
        
        for record in operation_records:
            if record.get("effect") == "良好":
                successful.append(f"{record.get('type', '操作')}：{record.get('date', '')}")
            elif record.get("effect") == "不佳":
                failed.append(f"{record.get('type', '操作')}：{record.get('date', '')}")
        
        return summary, successful, failed
    
    def _extract_lessons(
        self,
        weather_anomalies: List[str],
        operation_records: List[Dict[str, Any]]
    ) -> List[str]:
        """提取经验教训"""
        lessons = []
        
        for anomaly in weather_anomalies:
            if "霜冻" in anomaly:
                lessons.append("霜冻前应提前采取防护措施")
            if "高温" in anomaly:
                lessons.append("高温天气应增加灌溉频次")
            if "降水偏多" in anomaly:
                lessons.append("多雨季节注意排水防涝")
        
        if not lessons:
            lessons.append("气象条件正常，继续保持")
        
        return lessons
    
    def _generate_future_recommendations(
        self,
        lessons_learned: List[str]
    ) -> List[str]:
        """生成未来建议"""
        recommendations = []
        
        for lesson in lessons_learned:
            if "霜冻" in lesson:
                recommendations.append("关注天气预报，提前做好防霜准备")
            if "高温" in lesson:
                recommendations.append("高温季节增加灌溉，注意遮阳")
            if "排水" in lesson:
                recommendations.append("雨季前疏通排水沟渠")
        
        if not recommendations:
            recommendations.append("继续按常规管理")
        
        return recommendations
    
    def get_review(self, review_id: str) -> Optional[HistoricalReview]:
        """获取复盘记录"""
        return self.reviews.get(review_id)

