# -*- coding: utf-8 -*-
"""
合规与边界工具集
实现建议分级、免责提示、不确定性说明
"""
from typing import Dict, List, Optional, Any, Tuple
from datetime import date
from src.models import (
    AdviceLevel, UncertaintyLevel,
    AdviceClassification
)


class AdviceClassificationTool:
    """建议分级与合规工具"""
    
    def __init__(self):
        self.name = "advice_classification"
        self.description = "建议分级与免责提示"
        
        self.advice_rules = {
            AdviceLevel.REFERENCE: {
                "disclaimer": "本建议仅供参考，请结合实际情况判断",
                "requires_consultation": False
            },
            AdviceLevel.PROFESSIONAL: {
                "disclaimer": "本建议基于专业分析，建议结合本地实际执行",
                "requires_consultation": False
            },
            AdviceLevel.HIGH_RISK: {
                "disclaimer": "⚠️ 本建议涉及高危操作，请务必咨询当地农技人员",
                "requires_consultation": True
            },
            AdviceLevel.REGULATED: {
                "disclaimer": "⚠️ 本建议涉及法规限制，请严格遵守当地农药管理规范",
                "requires_consultation": True
            }
        }
        
        self.high_risk_keywords = [
            "农药", "杀虫剂", "杀菌剂", "除草剂",
            "熏蒸", "剧毒", "高毒"
        ]
        
        self.regulated_keywords = [
            "禁用农药", "限用农药", "农药残留",
            "安全间隔期", "最大残留限量"
        ]
    
    def classify_advice(
        self,
        advice_id: str,
        content: str,
        forecast_days: int = 1
    ) -> AdviceClassification:
        """
        分类建议
        
        Args:
            advice_id: 建议ID
            content: 建议内容
            forecast_days: 预报天数
        
        Returns:
            建议分类结果
        """
        advice_level = AdviceLevel.REFERENCE
        
        for keyword in self.high_risk_keywords:
            if keyword in content:
                advice_level = AdviceLevel.HIGH_RISK
                break
        
        for keyword in self.regulated_keywords:
            if keyword in content:
                advice_level = AdviceLevel.REGULATED
                break
        
        if advice_level == AdviceLevel.REFERENCE:
            if any(word in content for word in ["建议", "推荐", "适宜"]):
                advice_level = AdviceLevel.PROFESSIONAL
        
        uncertainty = self._determine_uncertainty(forecast_days)
        
        confidence_score = self._calculate_confidence(forecast_days, advice_level)
        
        rule = self.advice_rules[advice_level]
        
        regulatory_notes = None
        if advice_level == AdviceLevel.REGULATED:
            regulatory_notes = [
                "请严格遵守《农药管理条例》",
                "注意农药安全间隔期",
                "避免使用禁用农药",
                "做好农药使用记录"
            ]
        
        return AdviceClassification(
            advice_id=advice_id,
            advice_level=advice_level,
            content=content,
            uncertainty=uncertainty,
            confidence_score=confidence_score,
            disclaimer=rule["disclaimer"],
            requires_local_consultation=rule["requires_consultation"],
            regulatory_notes=regulatory_notes
        )
    
    def _determine_uncertainty(self, forecast_days: int) -> UncertaintyLevel:
        """确定不确定性等级"""
        if forecast_days <= 3:
            return UncertaintyLevel.HIGH_CONFIDENCE
        elif forecast_days <= 7:
            return UncertaintyLevel.MEDIUM_CONFIDENCE
        elif forecast_days <= 15:
            return UncertaintyLevel.LOW_CONFIDENCE
        else:
            return UncertaintyLevel.VERY_LOW_CONFIDENCE
    
    def _calculate_confidence(
        self,
        forecast_days: int,
        advice_level: AdviceLevel
    ) -> float:
        """计算置信度"""
        base_confidence = {
            AdviceLevel.REFERENCE: 0.6,
            AdviceLevel.PROFESSIONAL: 0.7,
            AdviceLevel.HIGH_RISK: 0.5,
            AdviceLevel.REGULATED: 0.5
        }
        
        time_decay = max(0, 1 - forecast_days * 0.03)
        
        return base_confidence[advice_level] * time_decay
    
    def add_disclaimer_to_content(
        self,
        content: str,
        classification: AdviceClassification
    ) -> str:
        """
        为内容添加免责声明
        
        Args:
            content: 原始内容
            classification: 建议分类
        
        Returns:
            添加免责声明后的内容
        """
        disclaimer_text = f"\n\n---\n**免责声明**：{classification.disclaimer}"
        
        if classification.uncertainty != UncertaintyLevel.HIGH_CONFIDENCE:
            uncertainty_text = {
                UncertaintyLevel.MEDIUM_CONFIDENCE: "（4-7天预报，置信度中等）",
                UncertaintyLevel.LOW_CONFIDENCE: "（8-15天预报，置信度较低）",
                UncertaintyLevel.VERY_LOW_CONFIDENCE: "（>15天预报，置信度极低，仅供参考）"
            }
            disclaimer_text += f"\n**不确定性说明**：{uncertainty_text[classification.uncertainty]}"
        
        if classification.requires_local_consultation:
            disclaimer_text += "\n**重要提示**：建议咨询当地农技人员后再执行。"
        
        if classification.regulatory_notes:
            disclaimer_text += "\n\n**法规注意事项**："
            for note in classification.regulatory_notes:
                disclaimer_text += f"\n- {note}"
        
        return content + disclaimer_text
    
    def validate_pesticide_recommendation(
        self,
        pesticide_name: str,
        crop_type: str
    ) -> Dict[str, Any]:
        """
        验证农药推荐
        
        Args:
            pesticide_name: 农药名称
            crop_type: 作物类型
        
        Returns:
            验证结果
        """
        banned_pesticides = [
            "甲胺磷", "对硫磷", "甲基对硫磷",
            "磷胺", "久效磷", "六六六", "滴滴涕"
        ]
        
        restricted_pesticides = {
            "氧化乐果": ["蔬菜", "茶叶", "果树"],
            "克百威": ["蔬菜", "果树"],
            "涕灭威": ["蔬菜", "果树"]
        }
        
        result = {
            "pesticide": pesticide_name,
            "crop": crop_type,
            "is_banned": False,
            "is_restricted": False,
            "warning": None,
            "recommendation": None
        }
        
        if pesticide_name in banned_pesticides:
            result["is_banned"] = True
            result["warning"] = f"⚠️ {pesticide_name}为禁用农药，严禁使用！"
            result["recommendation"] = "请选择其他合规农药替代"
            return result
        
        if pesticide_name in restricted_pesticides:
            restricted_crops = restricted_pesticides[pesticide_name]
            if crop_type in restricted_crops:
                result["is_restricted"] = True
                result["warning"] = f"⚠️ {pesticide_name}在{crop_type}上限用，请谨慎使用"
                result["recommendation"] = "请严格遵守使用规范，注意安全间隔期"
        
        if not result["warning"]:
            result["recommendation"] = f"{pesticide_name}可用于{crop_type}，请按推荐剂量使用"
        
        return result


class UncertaintyManager:
    """不确定性管理工具"""
    
    def __init__(self):
        self.name = "uncertainty_manager"
        self.description = "气象预报不确定性说明"
        
        self.forecast_accuracy = {
            1: 0.95,
            2: 0.90,
            3: 0.85,
            4: 0.80,
            5: 0.75,
            6: 0.70,
            7: 0.65,
            10: 0.55,
            15: 0.45
        }
    
    def get_confidence_label(
        self,
        forecast_days: int
    ) -> Tuple[str, float]:
        """
        获取置信度标签
        
        Args:
            forecast_days: 预报天数
        
        Returns:
            (标签, 置信度)
        """
        if forecast_days <= 3:
            return "高置信度", 0.85
        elif forecast_days <= 7:
            return "中等置信度", 0.70
        elif forecast_days <= 15:
            return "低置信度", 0.50
        else:
            return "极低置信度", 0.30
    
    def add_uncertainty_warning(
        self,
        content: str,
        forecast_days: int,
        operation_type: str
    ) -> str:
        """
        添加不确定性警告
        
        Args:
            content: 原始内容
            forecast_days: 预报天数
            operation_type: 操作类型
        
        Returns:
            添加警告后的内容
        """
        label, confidence = self.get_confidence_label(forecast_days)
        
        if forecast_days <= 3:
            return content
        
        warning = f"\n\n**预报不确定性提示**：\n"
        warning += f"- 本建议基于{forecast_days}天天气预报，{label}（置信度{confidence*100:.0f}%）\n"
        
        if forecast_days <= 7:
            warning += "- 建议在执行前再次确认最新天气预报\n"
        elif forecast_days <= 15:
            warning += "- 远期预报不确定性较大，建议临近时再次确认\n"
            warning += "- 请做好备选方案准备\n"
        else:
            warning += "- 远期预报仅供参考，请以临近预报为准\n"
            warning += "- 建议制定多种应对方案\n"
        
        high_risk_operations = ["喷药", "收获", "播种"]
        if operation_type in high_risk_operations and forecast_days > 5:
            warning += f"\n⚠️ {operation_type}操作对天气敏感，建议临近时再次确认！\n"
        
        return content + warning
    
    def suggest_decision_timing(
        self,
        operation_type: str,
        planned_date: date,
        current_date: date
    ) -> Dict[str, Any]:
        """
        建议决策时机
        
        Args:
            operation_type: 操作类型
            planned_date: 计划日期
            current_date: 当前日期
        
        Returns:
            决策时机建议
        """
        days_ahead = (planned_date - current_date).days
        
        suggestion = {
            "operation": operation_type,
            "planned_date": planned_date,
            "days_ahead": days_ahead,
            "recommendation": "",
            "check_points": []
        }
        
        if days_ahead <= 1:
            suggestion["recommendation"] = "可以立即执行决策"
            suggestion["check_points"] = ["确认当前天气"]
        elif days_ahead <= 3:
            suggestion["recommendation"] = "建议明天再次确认后执行"
            suggestion["check_points"] = ["明天查看最新预报", "准备备选方案"]
        elif days_ahead <= 7:
            suggestion["recommendation"] = "建议提前1-2天再次确认"
            suggestion["check_points"] = [
                "提前2天查看预报",
                "提前1天最终确认",
                "准备备选方案"
            ]
        else:
            suggestion["recommendation"] = "远期计划，建议临近时重新评估"
            suggestion["check_points"] = [
                "提前7天初步确认",
                "提前3天再次确认",
                "提前1天最终确认",
                "准备多种备选方案"
            ]
        
        return suggestion

