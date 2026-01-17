from enum import Enum
from dataclasses import dataclass, asdict

class WeatherType(Enum):
    SUNNY = "晴天"
    RAINY = "雨天"
    SNOWY = "雪天"
    CLOUDY = "多云"
    STORM = "暴风雨"

class Season(Enum):
    SPRING = "春季"
    SUMMER = "夏季"
    AUTUMN = "秋季"
    WINTER = "冬季"

@dataclass
class WeatherState:
    season: str
    weather: str
    temperature: int
    date_str: str  # e.g. "第1年 春季 1日"
    day_counter: int # Absolute days passed

    def to_dict(self):
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data):
        return cls(**data)
