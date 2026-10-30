# -*- coding: utf-8 -*-
"""
高德地图地理编码工具类
集成IP定位和地理编码API
"""
import requests
import time
from typing import Optional, Dict, Tuple


class AmapGeocoding:
    """高德地图地理编码工具"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.last_request_time = 0
        self.request_delay = 0.2  # 请求间隔，避免并发限制
    
    def _wait_for_rate_limit(self):
        """等待以避免超过并发限制"""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.request_delay:
            time.sleep(self.request_delay - elapsed)
        self.last_request_time = time.time()
    
    def get_location_by_ip(self, ip: str = None) -> Dict:
        """
        通过IP获取位置
        
        Args:
            ip: IP地址（可选，不传则使用当前IP）
        
        Returns:
            {
                "status": True/False,
                "latitude": 纬度,
                "longitude": 经度,
                "province": "省份",
                "city": "城市",
                "adcode": "区域编码",
                "message": "提示信息"
            }
        """
        self._wait_for_rate_limit()
        
        url = "https://restapi.amap.com/v3/ip"
        params = {
            "key": self.api_key,
            "output": "JSON"
        }
        
        if ip:
            params["ip"] = ip
        
        try:
            response = requests.get(url, params=params, timeout=5)
            data = response.json()
            
            if data.get("status") == "1":
                province = data.get("province", "")
                city = data.get("city", "")
                adcode = data.get("adcode", "")
                rectangle = data.get("rectangle", "")
                
                # 从rectangle提取中心点
                if rectangle:
                    bottom_left, top_right = rectangle.split(";")
                    bl_lng, bl_lat = bottom_left.split(",")
                    tr_lng, tr_lat = top_right.split(",")
                    
                    longitude = (float(bl_lng) + float(tr_lng)) / 2
                    latitude = (float(bl_lat) + float(tr_lat)) / 2
                    
                    return {
                        "status": True,
                        "latitude": latitude,
                        "longitude": longitude,
                        "province": province,
                        "city": city,
                        "adcode": adcode,
                        "message": "IP定位成功"
                    }
                
                return {
                    "status": False,
                    "message": "未找到位置信息"
                }
            else:
                return {
                    "status": False,
                    "message": f"API错误: {data.get('info', '未知错误')}"
                }
        
        except Exception as e:
            return {
                "status": False,
                "message": f"请求失败: {str(e)}"
            }
    
    def get_coordinates_by_address(
        self,
        address: str,
        city: str = None
    ) -> Dict:
        """
        通过地址获取经纬度
        
        Args:
            address: 地址（如："河南省郑州市金水区"）
            city: 可选，指定城市提高准确性
        
        Returns:
            {
                "status": True/False,
                "latitude": 纬度,
                "longitude": 经度,
                "formatted_address": "格式化地址",
                "province": "省份",
                "city": "城市",
                "district": "区县",
                "adcode": "区域编码",
                "message": "提示信息"
            }
        """
        self._wait_for_rate_limit()
        
        url = "https://restapi.amap.com/v3/geocode/geo"
        params = {
            "key": self.api_key,
            "address": address,
            "output": "JSON"
        }
        
        if city:
            params["city"] = city
        
        try:
            response = requests.get(url, params=params, timeout=5)
            data = response.json()
            
            if data.get("status") == "1" and data.get("geocodes"):
                geocode = data["geocodes"][0]
                location = geocode.get("location", "")
                
                if location:
                    longitude, latitude = location.split(",")
                    
                    return {
                        "status": True,
                        "latitude": float(latitude),
                        "longitude": float(longitude),
                        "formatted_address": geocode.get("formatted_address", ""),
                        "province": geocode.get("province", ""),
                        "city": geocode.get("city", ""),
                        "district": geocode.get("district", ""),
                        "adcode": geocode.get("adcode", ""),
                        "level": geocode.get("level", ""),
                        "message": "地理编码成功"
                    }
                
                return {
                    "status": False,
                    "message": "未找到位置信息"
                }
            else:
                return {
                    "status": False,
                    "message": f"API错误: {data.get('info', '未知错误')}"
                }
        
        except Exception as e:
            return {
                "status": False,
                "message": f"请求失败: {str(e)}"
            }
    
    def get_districts(self, keywords: str = None, subdistrict: int = 1) -> Dict:
        """
        查询行政区划
        
        Args:
            keywords: 查询关键词（如："河南"）
            subdistrict: 子级层级（1=省，2=市，3=区县）
        
        Returns:
            {
                "status": True/False,
                "districts": [行政区划列表],
                "message": "提示信息"
            }
        """
        self._wait_for_rate_limit()
        
        url = "https://restapi.amap.com/v3/config/district"
        params = {
            "key": self.api_key,
            "keywords": keywords or "中国",
            "subdistrict": subdistrict,
            "output": "JSON"
        }
        
        try:
            response = requests.get(url, params=params, timeout=5)
            data = response.json()
            
            if data.get("status") == "1" and data.get("districts"):
                return {
                    "status": True,
                    "districts": data["districts"],
                    "message": "查询成功"
                }
            
            return {
                "status": False,
                "message": f"API错误: {data.get('info', '未知错误')}"
            }
        
        except Exception as e:
            return {
                "status": False,
                "message": f"请求失败: {str(e)}"
            }

