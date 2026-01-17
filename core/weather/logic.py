import random
import time
from pathlib import Path
import json
from .models import WeatherState, Season, WeatherType
from ..common.data_manager import DataManager

class WeatherLogic:
    def __init__(self, data_manager: DataManager):
        self.dm = data_manager
        self.data_path = Path(self.dm.root) / 'data' / 'world'
        self.data_path.mkdir(parents=True, exist_ok=True)
        self.weather_file = self.data_path / 'weather.json'
        
        self.state = self._load_state()

    def _load_state(self) -> WeatherState:
        if self.weather_file.exists():
            try:
                data = json.loads(self.weather_file.read_text(encoding='utf-8'))
                return WeatherState.from_dict(data)
            except:
                pass
        # Default start
        return WeatherState(
            season=Season.SPRING.value,
            weather=WeatherType.SUNNY.value,
            temperature=20,
            date_str="第1年 春季 1日",
            day_counter=1
        )

    def save_state(self):
        self.weather_file.write_text(json.dumps(self.state.to_dict(), ensure_ascii=False, indent=2), encoding='utf-8')

    def get_current_weather(self):
        # Calculate days based on real time or just keep static until updated?
        # Let's make it update every 4 hours real time = 1 game day? 
        # Or simpler: Update daily at 00:00?
        # For now, let's stick to an explicit update method that can be called by a scheduler or command.
        return self.state

    def update_weather(self):
        """Advance one day"""
        self.state.day_counter += 1
        
        # Calculate Date
        days_per_season = 30
        total_days = self.state.day_counter
        
        year = (total_days - 1) // (days_per_season * 4) + 1
        season_idx = ((total_days - 1) // days_per_season) % 4
        day_in_season = (total_days - 1) % days_per_season + 1
        
        seasons = [Season.SPRING, Season.SUMMER, Season.AUTUMN, Season.WINTER]
        current_season = seasons[season_idx]
        
        self.state.season = current_season.value
        self.state.date_str = f"第{year}年 {current_season.value} {day_in_season}日"
        
        # Random Weather based on Season
        self.state.weather = self._generate_weather(current_season).value
        self.state.temperature = self._generate_temp(current_season, self.state.weather)
        
        self.save_state()
        return self.state

    def _generate_weather(self, season: Season) -> WeatherType:
        weights = {
            Season.SPRING: {WeatherType.SUNNY: 50, WeatherType.CLOUDY: 30, WeatherType.RAINY: 20, WeatherType.STORM: 0, WeatherType.SNOWY: 0},
            Season.SUMMER: {WeatherType.SUNNY: 60, WeatherType.CLOUDY: 20, WeatherType.RAINY: 10, WeatherType.STORM: 10, WeatherType.SNOWY: 0},
            Season.AUTUMN: {WeatherType.SUNNY: 40, WeatherType.CLOUDY: 40, WeatherType.RAINY: 20, WeatherType.STORM: 0, WeatherType.SNOWY: 0},
            Season.WINTER: {WeatherType.SUNNY: 30, WeatherType.CLOUDY: 30, WeatherType.RAINY: 0, WeatherType.STORM: 10, WeatherType.SNOWY: 30},
        }
        w_map = weights[season]
        choices = list(w_map.keys())
        probs = list(w_map.values())
        return random.choices(choices, weights=probs, k=1)[0]

    def _generate_temp(self, season: Season, weather: str) -> int:
        base_temps = {
            Season.SPRING: 15,
            Season.SUMMER: 30,
            Season.AUTUMN: 18,
            Season.WINTER: 0
        }
        temp = base_temps[season] + random.randint(-5, 5)
        if weather == WeatherType.RAINY.value:
            temp -= 3
        if weather == WeatherType.SNOWY.value:
            temp -= 5
        if weather == WeatherType.SUNNY.value:
            temp += 3
        return temp
