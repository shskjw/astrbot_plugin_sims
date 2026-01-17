from pathlib import Path
import uuid
import json
import random
from typing import Optional, List, Dict, Any
from datetime import datetime

from ..common.data_manager import DataManager
from ..common.cooldown import check_cooldown, set_cooldown
from .models import (
    CinemaInfo, Theater, Movie, Facility, CinemaStaff, ScheduleItem,
    CinemaRankingEntry,
    THEATER_TYPES, FACILITY_TYPES, STAFF_TYPES, MOVIE_GENRES, AVAILABLE_MOVIES
)


class CinemaLogic:
    def __init__(self, data_manager: Optional[DataManager] = None):
        self.dm = data_manager or DataManager()
        self.data_path = Path(self.dm.root) / 'data' / 'cinema'
        self.data_path.mkdir(parents=True, exist_ok=True)

    # ========== 文件操作 ==========
    def _cinemas_file(self) -> Path:
        return self.data_path / 'cinemas.json'

    def _movies_file(self) -> Path:
        return self.data_path / 'movies.json'

    def _load_cinemas(self) -> dict:
        p = self._cinemas_file()
        if not p.exists():
            return {}
        return json.loads(p.read_text(encoding='utf-8'))

    def _save_cinemas(self, data: dict):
        p = self._cinemas_file()
        p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')

    def _load_movies(self) -> List[dict]:
        p = self._movies_file()
        if not p.exists():
            return []
        return json.loads(p.read_text(encoding='utf-8')).get('movies', [])

    # ========== 电影院数据操作 ==========
    def _get_user_cinema(self, user_id: str) -> Optional[CinemaInfo]:
        """获取用户的电影院"""
        cinemas = self._load_cinemas()
        if user_id in cinemas:
            return CinemaInfo(**cinemas[user_id])
        return None

    def _save_user_cinema(self, user_id: str, cinema: CinemaInfo):
        """保存用户的电影院"""
        cinemas = self._load_cinemas()
        cinemas[user_id] = cinema.dict()
        self._save_cinemas(cinemas)

    def _update_cinema_revenue(self, cinema: CinemaInfo) -> CinemaInfo:
        """更新电影院收入"""
        last_update = datetime.fromisoformat(cinema.last_update)
        now = datetime.now()
        hours_passed = (now - last_update).total_seconds() / 3600
        
        if hours_passed < 1:
            return cinema
        
        hours = int(hours_passed)
        
        # 计算每小时收入
        hourly_revenue = 0
        for theater in cinema.theaters:
            base_revenue = THEATER_TYPES[theater.type]['capacity'] * 0.5 * 30  # 50%上座率 * 30元均价
            reputation_mult = cinema.reputation / 100
            hourly_revenue += int(base_revenue * reputation_mult)
        
        # 设施加成
        facility_mult = 1.0
        for f in cinema.facilities:
            facility_mult += (f.revenue_multiplier - 1)
        
        hourly_revenue = int(hourly_revenue * facility_mult)
        
        # 计算总收入
        revenue = hourly_revenue * hours
        cinema.daily_revenue = hourly_revenue
        cinema.total_revenue += revenue
        
        # 扣除成本
        cost = (cinema.maintenance_cost + cinema.staff_cost) * hours / 720  # 月成本/720小时
        
        cinema.last_update = now.isoformat()
        
        return cinema

    # ========== 核心功能 ==========
    def buy_cinema(self, user_id: str, name: str = None) -> CinemaInfo:
        """购买电影院"""
        rem = check_cooldown(user_id, 'cinema', 'buy')
        if rem > 0:
            raise RuntimeError(f"cooldown:{rem}")
        
        existing = self._get_user_cinema(user_id)
        if existing:
            raise ValueError("你已经拥有一家电影院了！")
        
        # 检查资金
        cinema_cost = 100000
        user = self.dm.load_user(user_id) or {}
        if user.get('money', 0) < cinema_cost:
            raise ValueError(f"购买电影院需要{cinema_cost}元启动资金！")
        
        # 扣除资金
        user['money'] -= cinema_cost
        self.dm.save_user(user_id, user)
        
        # 创建电影院
        cinema_id = str(uuid.uuid4())[:8]
        user_name = user.get('name', f'用户{user_id[:6]}')
        cinema_name = name or f"{user_name}的电影院"
        
        cinema = CinemaInfo(
            id=cinema_id,
            owner_id=user_id,
            name=cinema_name
        )
        
        self._save_user_cinema(user_id, cinema)
        
        set_cooldown(user_id, 'cinema', 'buy', 60)
        
        return cinema

    def get_cinema_info(self, user_id: str) -> CinemaInfo:
        """获取电影院信息"""
        rem = check_cooldown(user_id, 'cinema', 'info')
        if rem > 0:
            raise RuntimeError(f"cooldown:{rem}")
        
        cinema = self._get_user_cinema(user_id)
        if not cinema:
            raise ValueError("你还没有电影院！请使用【购买电影院】指令购买一家电影院。")
        
        # 更新收入
        cinema = self._update_cinema_revenue(cinema)
        self._save_user_cinema(user_id, cinema)
        
        set_cooldown(user_id, 'cinema', 'info', 3)
        
        return cinema

    def buy_theater(self, user_id: str, theater_type: str) -> dict:
        """购买影厅"""
        rem = check_cooldown(user_id, 'cinema', 'theater')
        if rem > 0:
            raise RuntimeError(f"cooldown:{rem}")
        
        cinema = self._get_user_cinema(user_id)
        if not cinema:
            raise ValueError("你还没有电影院！")
        
        if theater_type not in THEATER_TYPES:
            available = '、'.join(THEATER_TYPES.keys())
            raise ValueError(f"无效的影厅类型！可选：{available}")
        
        config = THEATER_TYPES[theater_type]
        
        # 检查是否已有同类型
        existing_count = sum(1 for t in cinema.theaters if t.type == theater_type)
        max_theaters = cinema.level * 2
        if len(cinema.theaters) >= max_theaters:
            raise ValueError(f"当前电影院等级最多拥有{max_theaters}个影厅！")
        
        # 检查资金
        cost = config['cost']
        user = self.dm.load_user(user_id) or {}
        if user.get('money', 0) < cost:
            raise ValueError(f"购买{config['name']}需要{cost}元，资金不足！")
        
        # 购买
        user['money'] -= cost
        
        theater_id = f"TH{uuid.uuid4().hex[:6].upper()}"
        theater_name = f"{config['name']}{len(cinema.theaters) + 1}"
        
        theater = Theater(
            id=theater_id,
            name=theater_name,
            type=theater_type,
            capacity=config['capacity'],
            maintenance_cost=config['maintenance_cost']
        )
        cinema.theaters.append(theater)
        cinema.maintenance_cost += config['maintenance_cost']
        
        self.dm.save_user(user_id, user)
        self._save_user_cinema(user_id, cinema)
        
        set_cooldown(user_id, 'cinema', 'theater', 30)
        
        return {
            "theater_id": theater_id,
            "theater_name": theater_name,
            "type": theater_type,
            "type_name": config['name'],
            "capacity": config['capacity'],
            "cost": cost
        }

    def upgrade_theater(self, user_id: str, theater_id: str) -> dict:
        """升级影厅"""
        rem = check_cooldown(user_id, 'cinema', 'upgrade')
        if rem > 0:
            raise RuntimeError(f"cooldown:{rem}")
        
        cinema = self._get_user_cinema(user_id)
        if not cinema:
            raise ValueError("你还没有电影院！")
        
        # 查找影厅
        theater = None
        for t in cinema.theaters:
            if t.id == theater_id or t.name == theater_id:
                theater = t
                break
        
        if not theater:
            theater_list = ', '.join(f"{t.name}({t.id})" for t in cinema.theaters) or "无"
            raise ValueError(f"未找到该影厅！当前影厅：{theater_list}")
        
        config = THEATER_TYPES[theater.type]
        
        if not config['next_level']:
            raise ValueError("该影厅已达最高等级！")
        
        # 检查资金
        upgrade_cost = config['upgrade_cost']
        user = self.dm.load_user(user_id) or {}
        if user.get('money', 0) < upgrade_cost:
            raise ValueError(f"升级影厅需要{upgrade_cost}元，资金不足！")
        
        # 升级
        user['money'] -= upgrade_cost
        old_type = theater.type
        old_name = THEATER_TYPES[old_type]['name']
        
        new_type = config['next_level']
        new_config = THEATER_TYPES[new_type]
        
        # 更新维护成本
        cinema.maintenance_cost -= THEATER_TYPES[old_type]['maintenance_cost']
        cinema.maintenance_cost += new_config['maintenance_cost']
        
        theater.type = new_type
        theater.capacity = new_config['capacity']
        theater.maintenance_cost = new_config['maintenance_cost']
        
        self.dm.save_user(user_id, user)
        self._save_user_cinema(user_id, cinema)
        
        set_cooldown(user_id, 'cinema', 'upgrade', 60)
        
        return {
            "theater_name": theater.name,
            "old_type": old_name,
            "new_type": new_config['name'],
            "new_capacity": new_config['capacity'],
            "cost": upgrade_cost
        }

    def buy_movie(self, user_id: str, movie_title: str) -> dict:
        """购买电影版权"""
        rem = check_cooldown(user_id, 'cinema', 'movie')
        if rem > 0:
            raise RuntimeError(f"cooldown:{rem}")
        
        cinema = self._get_user_cinema(user_id)
        if not cinema:
            raise ValueError("你还没有电影院！")
        
        # 查找电影
        selected_movie = None
        selected_genre = None
        for genre, movies in AVAILABLE_MOVIES.items():
            for m in movies:
                if m['title'] == movie_title:
                    selected_movie = m
                    selected_genre = genre
                    break
            if selected_movie:
                break
        
        if not selected_movie:
            raise ValueError("未找到该电影！使用【电影列表】查看可购买的电影。")
        
        # 检查是否已拥有
        if any(m.id == selected_movie['id'] for m in cinema.movies):
            raise ValueError("你已经拥有该电影的版权了！")
        
        # 获取电影配置
        genre_config = MOVIE_GENRES[selected_genre]
        cost = genre_config['cost']
        
        user = self.dm.load_user(user_id) or {}
        if user.get('money', 0) < cost:
            raise ValueError(f"购买《{movie_title}》版权需要{cost}元，资金不足！")
        
        # 购买
        user['money'] -= cost
        
        movie = Movie(
            id=selected_movie['id'],
            title=selected_movie['title'],
            genre=selected_genre,
            duration=genre_config['duration'],
            base_price=genre_config['base_price'],
            popularity=selected_movie['popularity'],
            rating=selected_movie['rating'],
            cost=cost
        )
        cinema.movies.append(movie)
        
        self.dm.save_user(user_id, user)
        self._save_user_cinema(user_id, cinema)
        
        set_cooldown(user_id, 'cinema', 'movie', 30)
        
        return {
            "title": movie.title,
            "genre": genre_config['name'],
            "duration": movie.duration,
            "base_price": movie.base_price,
            "popularity": movie.popularity,
            "rating": movie.rating,
            "cost": cost
        }

    def schedule_movie(self, user_id: str, theater_id: str, movie_title: str, time: str) -> dict:
        """排片"""
        rem = check_cooldown(user_id, 'cinema', 'schedule')
        if rem > 0:
            raise RuntimeError(f"cooldown:{rem}")
        
        cinema = self._get_user_cinema(user_id)
        if not cinema:
            raise ValueError("你还没有电影院！")
        
        # 查找影厅
        theater = None
        for t in cinema.theaters:
            if t.id == theater_id or t.name == theater_id:
                theater = t
                break
        
        if not theater:
            raise ValueError("未找到该影厅！")
        
        # 查找电影
        movie = None
        for m in cinema.movies:
            if m.title == movie_title:
                movie = m
                break
        
        if not movie:
            raise ValueError("未找到该电影！请先购买电影版权。")
        
        # 验证时间格式
        import re
        if not re.match(r'^([01]?[0-9]|2[0-3]):[0-5][0-9]$', time):
            raise ValueError("请输入正确的时间格式（24小时制，如：14:30）")
        
        # 检查时间冲突
        for s in theater.schedule:
            if abs(int(s['time'].replace(':', '')) - int(time.replace(':', ''))) < movie.duration // 60 * 100:
                raise ValueError("该时间段已有其他电影排片！")
        
        # 添加排片
        schedule_item = {
            "movie_id": movie.id,
            "movie_title": movie.title,
            "time": time,
            "duration": movie.duration,
            "price": movie.base_price
        }
        theater.schedule.append(schedule_item)
        theater.schedule.sort(key=lambda x: x['time'])
        
        self._save_user_cinema(user_id, cinema)
        
        set_cooldown(user_id, 'cinema', 'schedule', 15)
        
        return {
            "theater_name": theater.name,
            "movie_title": movie.title,
            "time": time,
            "duration": movie.duration,
            "price": movie.base_price
        }

    def buy_facility(self, user_id: str, facility_type: str) -> dict:
        """购买设施"""
        rem = check_cooldown(user_id, 'cinema', 'facility')
        if rem > 0:
            raise RuntimeError(f"cooldown:{rem}")
        
        cinema = self._get_user_cinema(user_id)
        if not cinema:
            raise ValueError("你还没有电影院！")
        
        if facility_type not in FACILITY_TYPES:
            available = '、'.join(FACILITY_TYPES.keys())
            raise ValueError(f"无效的设施类型！可选：{available}")
        
        config = FACILITY_TYPES[facility_type]
        
        # 检查是否已拥有
        if any(f.type == facility_type for f in cinema.facilities):
            raise ValueError(f"你已经拥有{config['name']}了！")
        
        # 检查资金
        cost = config['cost']
        user = self.dm.load_user(user_id) or {}
        if user.get('money', 0) < cost:
            raise ValueError(f"购买{config['name']}需要{cost}元，资金不足！")
        
        # 购买
        user['money'] -= cost
        
        facility = Facility(
            type=facility_type,
            name=config['name'],
            maintenance_cost=config['maintenance_cost'],
            revenue_multiplier=config['revenue_multiplier']
        )
        cinema.facilities.append(facility)
        cinema.maintenance_cost += config['maintenance_cost']
        
        self.dm.save_user(user_id, user)
        self._save_user_cinema(user_id, cinema)
        
        set_cooldown(user_id, 'cinema', 'facility', 30)
        
        return {
            "name": config['name'],
            "cost": cost,
            "maintenance_cost": config['maintenance_cost'],
            "revenue_multiplier": config['revenue_multiplier'],
            "description": config['description']
        }

    def hire_staff(self, user_id: str, staff_type: str) -> dict:
        """雇佣员工"""
        rem = check_cooldown(user_id, 'cinema', 'hire')
        if rem > 0:
            raise RuntimeError(f"cooldown:{rem}")
        
        cinema = self._get_user_cinema(user_id)
        if not cinema:
            raise ValueError("你还没有电影院！")
        
        if staff_type not in STAFF_TYPES:
            available = '、'.join(STAFF_TYPES.keys())
            raise ValueError(f"无效的员工类型！可选：{available}")
        
        config = STAFF_TYPES[staff_type]
        
        # 检查资金
        salary = config['salary']
        user = self.dm.load_user(user_id) or {}
        if user.get('money', 0) < salary:
            raise ValueError(f"雇佣{config['name']}需要{salary}元首月工资，资金不足！")
        
        # 雇佣
        user['money'] -= salary
        
        staff_id = f"STF{uuid.uuid4().hex[:6].upper()}"
        staff_count = sum(1 for s in cinema.staff if s.type == staff_type)
        staff_name = f"{config['name']}{staff_count + 1}"
        
        staff = CinemaStaff(
            id=staff_id,
            type=staff_type,
            name=staff_name,
            level=1,
            efficiency=config['efficiency'],
            salary=salary
        )
        cinema.staff.append(staff)
        cinema.staff_cost += salary
        
        self.dm.save_user(user_id, user)
        self._save_user_cinema(user_id, cinema)
        
        set_cooldown(user_id, 'cinema', 'hire', 30)
        
        return {
            "staff_id": staff_id,
            "name": staff_name,
            "type_name": config['name'],
            "salary": salary,
            "efficiency": config['efficiency'],
            "description": config['description']
        }

    def train_staff(self, user_id: str, staff_id: str) -> dict:
        """培训员工"""
        rem = check_cooldown(user_id, 'cinema', 'train')
        if rem > 0:
            raise RuntimeError(f"cooldown:{rem}")
        
        cinema = self._get_user_cinema(user_id)
        if not cinema:
            raise ValueError("你还没有电影院！")
        
        # 查找员工
        staff = None
        for s in cinema.staff:
            if s.id == staff_id or s.name == staff_id:
                staff = s
                break
        
        if not staff:
            staff_list = ', '.join(f"{s.name}({s.id})" for s in cinema.staff) or "无"
            raise ValueError(f"未找到该员工！当前员工：{staff_list}")
        
        config = STAFF_TYPES[staff.type]
        
        if staff.level >= config['max_level']:
            raise ValueError("该员工已达最高等级！")
        
        # 检查资金
        training_cost = config['training_cost']
        user = self.dm.load_user(user_id) or {}
        if user.get('money', 0) < training_cost:
            raise ValueError(f"培训员工需要{training_cost}元，资金不足！")
        
        # 培训
        user['money'] -= training_cost
        old_level = staff.level
        staff.level += 1
        staff.efficiency = config['efficiency'] * (1 + staff.level * 0.1)
        
        self.dm.save_user(user_id, user)
        self._save_user_cinema(user_id, cinema)
        
        set_cooldown(user_id, 'cinema', 'train', 60)
        
        return {
            "staff_name": staff.name,
            "old_level": old_level,
            "new_level": staff.level,
            "new_efficiency": staff.efficiency,
            "cost": training_cost
        }

    def collect_revenue(self, user_id: str) -> dict:
        """收取收入"""
        rem = check_cooldown(user_id, 'cinema', 'collect')
        if rem > 0:
            raise RuntimeError(f"cooldown:{rem}")
        
        cinema = self._get_user_cinema(user_id)
        if not cinema:
            raise ValueError("你还没有电影院！")
        
        # 更新收入
        cinema = self._update_cinema_revenue(cinema)
        
        # 计算可收取金额
        net_revenue = cinema.total_revenue
        if net_revenue <= 0:
            raise ValueError("当前没有可收取的收入！")
        
        # 收取
        user = self.dm.load_user(user_id) or {}
        user['money'] = user.get('money', 0) + net_revenue
        
        collected = net_revenue
        cinema.total_revenue = 0
        
        self.dm.save_user(user_id, user)
        self._save_user_cinema(user_id, cinema)
        
        set_cooldown(user_id, 'cinema', 'collect', 60)
        
        return {"collected": collected}

    def get_cinema_ranking(self, sort_by: str = "revenue") -> List[CinemaRankingEntry]:
        """获取电影院排行榜"""
        cinemas = self._load_cinemas()
        
        entries = []
        for uid, data in cinemas.items():
            user = self.dm.load_user(uid) or {}
            entries.append(CinemaRankingEntry(
                owner_id=uid,
                owner_name=user.get('name', f'用户{uid[:6]}'),
                cinema_name=data.get('name', '电影院'),
                total_revenue=data.get('total_revenue', 0),
                reputation=data.get('reputation', 50),
                theater_count=len(data.get('theaters', [])),
                movie_count=len(data.get('movies', []))
            ))
        
        # 排序
        if sort_by == "reputation":
            entries.sort(key=lambda x: x.reputation, reverse=True)
        else:
            entries.sort(key=lambda x: x.total_revenue, reverse=True)
        
        return entries[:20]

    def get_movie_list(self) -> dict:
        """获取可购买的电影列表"""
        result = {}
        for genre, movies in AVAILABLE_MOVIES.items():
            genre_config = MOVIE_GENRES[genre]
            result[genre_config['name']] = {
                "cost": genre_config['cost'],
                "base_price": genre_config['base_price'],
                "duration": genre_config['duration'],
                "movies": movies
            }
        return result

    def get_theater_types(self) -> List[dict]:
        """获取影厅类型"""
        return [
            {
                "type": t,
                "name": config['name'],
                "capacity": config['capacity'],
                "cost": config['cost'],
                "maintenance_cost": config['maintenance_cost'],
                "next_level": config['next_level'],
                "upgrade_cost": config['upgrade_cost']
            }
            for t, config in THEATER_TYPES.items()
        ]

    def get_facility_types(self) -> List[dict]:
        """获取设施类型"""
        return [
            {
                "type": t,
                "name": config['name'],
                "cost": config['cost'],
                "maintenance_cost": config['maintenance_cost'],
                "revenue_multiplier": config['revenue_multiplier'],
                "description": config['description']
            }
            for t, config in FACILITY_TYPES.items()
        ]

    def get_staff_types(self) -> List[dict]:
        """获取员工类型"""
        return [
            {
                "type": t,
                "name": config['name'],
                "salary": config['salary'],
                "efficiency": config['efficiency'],
                "training_cost": config['training_cost'],
                "max_level": config['max_level'],
                "description": config['description']
            }
            for t, config in STAFF_TYPES.items()
        ]

    # ========== 兼容旧接口 ==========
    def watch_movie(self, user_id: str, movie_id: str) -> dict:
        rem = check_cooldown(user_id, 'cinema', 'watch')
        if rem > 0:
            raise RuntimeError(f"cooldown:{rem}")
        movies = self._load_movies()
        movie = next((m for m in movies if m.get('id') == movie_id), None)
        if not movie:
            raise ValueError('电影不存在')
        price = movie.get('price', 10)
        user = self.dm.load_user(user_id) or {}
        if user.get('money', 0) < price:
            raise ValueError('金币不足')
        user['money'] = user.get('money', 0) - price
        self.dm.save_user(user_id, user)
        set_cooldown(user_id, 'cinema', 'watch', 5)
        return movie

    def list_movies(self):
        return self._load_movies()

    def create_theater(self, user_id: str, name: str) -> dict:
        user = self.dm.load_user(user_id) or {}
        if user.get('money', 0) < 1000:
            raise ValueError('创建电影院需要1000金币')
        user['money'] -= 1000
        self.dm.save_user(user_id, user)
        return {'user_id': user_id, 'name': name, 'level': 1, 'funds': 0}
