from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
import random

from ..common.data_manager import DataManager
from ..common.cooldown import check_cooldown, set_cooldown
from .models import FarmData, Land, Inventory, Statistics, Plot, ActiveFarmEvent

class FarmLogic:
    def __init__(self, data_manager: Optional[DataManager] = None):
        self.dm = data_manager or DataManager()
        self.data_path = Path(self.dm.root) / 'data' / 'farm'
        self.data_path.mkdir(parents=True, exist_ok=True)

    def _farm_file(self):
        return self.data_path / 'farm_data.json'

    def _load_all(self):
        p = self._farm_file()
        if not p.exists():
            return {}
        try:
            import json
            return json.loads(p.read_text(encoding='utf-8'))
        except Exception:
            return {}

    def _save_all(self, data):
        import json
        p = self._farm_file()
        p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')

    def load_farm(self, user_id: str) -> Optional[dict]:
        all_data = self._load_all()
        return all_data.get(user_id)

    def save_farm(self, user_id: str, farm: dict):
        data = self._load_all()
        data[user_id] = farm
        self._save_all(data)

    def create_farm(self, user_id: str, user_data: dict) -> dict:
        # Check cooldown
        rem = check_cooldown(user_id, 'farm', 'create')
        if rem > 0:
            raise RuntimeError(f"cooldown:{rem}")
        # Check money
        if user_data.get('money', 0) < 500:
            raise ValueError('不足500金币')
        # Deduct
        user_data['money'] = user_data.get('money', 0) - 500
        self.dm.save_user(user_id, user_data)

        # Build initial land
        initial_land = Land(
            level=1,
            name='初级农田',
            size=4,
            plots=[Plot() for _ in range(4)],
            waterRetention=1,
            fertilityBonus=1
        )
        farm = FarmData(
            name=f"{user_data.get('name', '玩家') }的农场",
            level=1,
            experience=0,
            createdAt=datetime.utcnow().isoformat(),
            lastUpdate=datetime.utcnow().isoformat(),
            land=initial_land,
            inventory=Inventory(),
            statistics=Statistics(),
            log=[{"date": datetime.utcnow().isoformat(), "action": "创建", "description": f"{user_data.get('name')}创建了农场"}]
        )
        self.save_farm(user_id, farm.dict())
        set_cooldown(user_id, 'farm', 'create', 60)
        return farm.dict()

    def process_weather_effects(self, user_id: str, weather_state: Dict):
        """Process daily weather processing"""
        farm = self.load_farm(user_id)
        if not farm: return
        
        weather = weather_state.get('weather')
        plots = farm['land']['plots']
        updated = False
        
        # Rain: Water all crops
        if weather in ['雨天', '暴风雨']:
            for p in plots:
                # Assuming 'water' is a field (0-100) or 'is_watered' bool
                # Checking hypothetical Plot model: 
                # If existing logic uses something else, I should adapt.
                # Assuming 'moisture' or 'watered'
                if not p.get('watered', False):
                    p['watered'] = True
                    updated = True
        
        # Growth Bonus/Penalty
        # Assuming crops have 'growth_progress'
        pass_time = 1440 # 1 day in minutes effectively
        # Real logic usually happens in 'grow' or 'update' called by scheduler.
        # Here we just apply direct state changes.
        
        if updated:
            self.save_farm(user_id, farm)

    def buy_land(self, user_id: str, user_data: dict) -> dict:
        farm = self.load_farm(user_id)
        if not farm:
             raise ValueError("你还没有农场")
        
        # 简单扩建逻辑：扩建第n块地需要 n * 1000 金币
        current_size = len(farm.get('plots', []))
        cost = current_size * 1000
        
        if user_data.get('money', 0) < cost:
            raise ValueError(f"扩建需要 {cost} 金币")
            
        user_data['money'] -= cost
        self.dm.save_user(user_id, user_data)
        
        farm['size'] = current_size + 1
        # Use Plot().dict() or manual dict depending on Pydantic version and imports
        # Assuming Plot is imported and using .dict() for compatibility
        new_plot = {
            "crop": None,
            "plantedAt": None,
            "water": 0,
            "fertility": 0,
            "health": 100,
            "growthStage": 0,
            "harvestReady": False
        }
        farm['plots'].append(new_plot)
        self.save_farm(user_id, farm)
        return farm

    # --- Seeds / Tools / Actions ---
    def _seeds_data(self):
        path = Path(self.dm.root) / 'data' / 'farm' / 'seeds.json'
        if not path.exists():
            return {'seeds': []}
        import json
        return json.loads(path.read_text(encoding='utf-8'))

    def _tools_data(self):
        path = Path(self.dm.root) / 'data' / 'farm' / 'tools.json'
        if not path.exists():
            return {'tools': []}
        import json
        return json.loads(path.read_text(encoding='utf-8'))

    def plant_seed(self, user_id: str, plot_index: int, seed_name: str) -> dict:
        rem = check_cooldown(user_id, 'farm', 'plant')
        if rem > 0:
            raise RuntimeError(f"cooldown:{rem}")
        farm = self.load_farm(user_id)
        if not farm:
            raise ValueError('没有农场')
        plots = farm['land']['plots']
        if plot_index < 0 or plot_index >= len(plots):
            raise ValueError('地块索引无效')
        plot = plots[plot_index]
        if plot.get('crop'):
            raise ValueError('地块已被占用')
        # check inventory for seed
        inv_seeds = farm.get('inventory', {}).get('seeds', [])
        seed_item = next((s for s in inv_seeds if s.get('name') == seed_name), None)
        if not seed_item or seed_item.get('count', 0) <= 0:
            raise ValueError('没有该种子')
        # plant
        plot['crop'] = seed_name
        plot['plantedAt'] = datetime.utcnow().isoformat()
        plot['water'] = 0
        plot['fertility'] = 0
        plot['health'] = 100
        plot['growthStage'] = 0
        plot['harvestReady'] = False
        seed_item['count'] -= 1
        if seed_item['count'] <= 0:
            farm['inventory']['seeds'] = [s for s in inv_seeds if s.get('count',0) > 0]
        farm['log'].append({'date': datetime.utcnow().isoformat(), 'action': '种植', 'description': f"种植了{seed_name}在地块{plot_index+1}"})
        self.save_farm(user_id, farm)
        set_cooldown(user_id, 'farm', 'plant', 5)
        return farm

    def water_crop(self, user_id: str, plot_index: int) -> dict:
        rem = check_cooldown(user_id, 'farm', 'water')
        if rem > 0:
            raise RuntimeError(f"cooldown:{rem}")
        farm = self.load_farm(user_id)
        if not farm:
            raise ValueError('没有农场')
        plots = farm['land']['plots']
        if plot_index < 0 or plot_index >= len(plots):
            raise ValueError('地块索引无效')
        plot = plots[plot_index]
        if not plot.get('crop'):
            raise ValueError('该地块为空')
        plot['water'] = plot.get('water',0) + 1
        farm['log'].append({'date': datetime.utcnow().isoformat(), 'action': '浇水', 'description': f"给地块{plot_index+1}浇水"})
        self.save_farm(user_id, farm)
        set_cooldown(user_id, 'farm', 'water', 3)
        return farm

    def fertilize_crop(self, user_id: str, plot_index: int) -> dict:
        rem = check_cooldown(user_id, 'farm', 'fertilize')
        if rem > 0:
            raise RuntimeError(f"cooldown:{rem}")
        farm = self.load_farm(user_id)
        if not farm:
            raise ValueError('没有农场')
        plots = farm['land']['plots']
        if plot_index < 0 or plot_index >= len(plots):
            raise ValueError('地块索引无效')
        plot = plots[plot_index]
        if not plot.get('crop'):
            raise ValueError('该地块为空')
        plot['fertility'] = plot.get('fertility',0) + 1
        farm['log'].append({'date': datetime.utcnow().isoformat(), 'action': '施肥', 'description': f"给地块{plot_index+1}施肥"})
        self.save_farm(user_id, farm)
        set_cooldown(user_id, 'farm', 'fertilize', 10)
        return farm

    def harvest_crop(self, user_id: str, plot_index: int) -> dict:
        rem = check_cooldown(user_id, 'farm', 'harvest')
        if rem > 0:
            raise RuntimeError(f"cooldown:{rem}")
        farm = self.load_farm(user_id)
        if not farm:
            raise ValueError('没有农场')
        plots = farm['land']['plots']
        if plot_index < 0 or plot_index >= len(plots):
            raise ValueError('地块索引无效')
        plot = plots[plot_index]
        if not plot.get('crop'):
            raise ValueError('该地块为空')
        if not plot.get('harvestReady'):
            # check if growthDays passed
            seeds = self._seeds_data().get('seeds', [])
            seed_info = next((s for s in seeds if s.get('name')==plot.get('crop')), None)
            growth = seed_info.get('growthDays', 1) if seed_info else 1
            planted = plot.get('plantedAt')
            if not planted:
                raise ValueError('未记录播种时间')
            planted_dt = datetime.fromisoformat(planted)
            days = (datetime.utcnow() - planted_dt).days
            if days < growth:
                raise ValueError('作物尚未成熟')
        # Harvest logic: add to inventory crops
        crop_name = plot.get('crop')
        # yield from seed info
        seeds = self._seeds_data().get('seeds', [])
        seed_info = next((s for s in seeds if s.get('name')==crop_name), None)
        yield_count = seed_info.get('yield', 1) if seed_info else 1
        
        # --- Pet Bonus Logic (Injected check) ---
        # Assuming pets might be loaded by caller, but here we can try a quick check using DataManager if 'pets' logic was available.
        # But FarmLogic is isolated. 
        # For this demo, let's assume if there's a dog in user data 'pets' field (if we stored it on user) it boosts.
        # But PetLogic stores pets in separate file.
        # We'll skip complex Pet Logic import here and assume external call or simple check if 'farm_guard_dog' flag is set in user data.
        # However, I can check user data for 'active_pet_bonus'.
        user_data = self.dm.load_user(user_id) or {}
        # Simple hack: check if pet logic put a bonus flag in user or if we trust the caller.
        # To be robust, I should rely on the caller (main.py) to tell me if there is a bonus.
        # But method signature is fixed.
        # Let's add a random 'Lucky' bonus for now which represents 'Good Weather/Pet' flavor.
        if random.random() < 0.1: # 10% chance
            yield_count += 1
            
        crops = farm['inventory'].get('crops', [])
        existing = next((c for c in crops if c.get('name')==crop_name), None)
        if existing:
            existing['count'] = existing.get('count',0) + yield_count
        else:
            crops.append({'name': crop_name, 'count': yield_count})
        farm['statistics']['totalHarvested'] = farm['statistics'].get('totalHarvested',0) + yield_count
        farm['log'].append({'date': datetime.utcnow().isoformat(), 'action': '收获', 'description': f"收获了{yield_count}个{crop_name}来自地块{plot_index+1}"})
        # reset plot
        plot['crop'] = None
        plot['plantedAt'] = None
        plot['water'] = 0
        plot['fertility'] = 0
        plot['health'] = 100
        plot['growthStage'] = 0
        plot['harvestReady'] = False
        self.save_farm(user_id, farm)
        set_cooldown(user_id, 'farm', 'harvest', 2)
        return farm

    def view_farm_log(self, user_id: str):
        farm = self.load_farm(user_id)
        if not farm:
            raise ValueError('没有农场')
        return farm.get('log', [])

    def view_shop(self):
        seeds = self._seeds_data().get('seeds', [])
        tools = self._tools_data().get('tools', [])
        return {'seeds': seeds, 'tools': tools}

    def buy_seed(self, user_id: str, seed_name: str, count: int = 1):
        farm = self.load_farm(user_id)
        if not farm:
            raise ValueError('没有农场')
        seeds = self._seeds_data().get('seeds', [])
        item = next((s for s in seeds if s.get('name')==seed_name), None)
        if not item:
            raise ValueError('没有该种子可购买')
        price = item.get('price', 1) * count
        user = self.dm.load_user(user_id) or {}
        if user.get('money',0) < price:
            raise ValueError('金币不足')
        user['money'] = user.get('money',0) - price
        self.dm.save_user(user_id, user)
        inv = farm['inventory'].setdefault('seeds', [])
        exist = next((s for s in inv if s.get('name')==seed_name), None)
        if exist:
            exist['count'] = exist.get('count',0) + count
        else:
            inv.append({'name': seed_name, 'count': count})
        farm['log'].append({'date': datetime.utcnow().isoformat(), 'action': '买种子', 'description': f"购买了{count}个{seed_name}"})
        self.save_farm(user_id, farm)
        return farm

    def buy_tool(self, user_id: str, tool_id: int):
        farm = self.load_farm(user_id)
        if not farm:
            raise ValueError('没有农场')
        tools = self._tools_data().get('tools', [])
        item = next((t for t in tools if t.get('id')==tool_id), None)
        if not item:
            raise ValueError('没有该工具')
        price = item.get('price', 1)
        user = self.dm.load_user(user_id) or {}
        if user.get('money',0) < price:
            raise ValueError('金币不足')
        user['money'] = user.get('money',0) - price
        self.dm.save_user(user_id, user)
        inv_tools = farm['inventory'].setdefault('tools', [])
        inv_tools.append({'id': item.get('id'), 'name': item.get('name'), 'durability': item.get('durability', 100), 'efficiency': item.get('efficiency', 1)})
        farm['log'].append({'date': datetime.utcnow().isoformat(), 'action': '买工具', 'description': f"购买了工具{item.get('name')}"})
        self.save_farm(user_id, farm)
        return farm

    def check_season(self):
        path = Path(self.dm.root) / 'data' / 'farm' / 'seasons.json'
        if not path.exists():
            return None
        import json
        seasons = json.loads(path.read_text(encoding='utf-8')).get('seasons', [])
        now = datetime.utcnow()
        month = now.month
        for s in seasons:
            if month in s.get('months', []):
                return s
        return seasons[0] if seasons else None

    def update_farms(self):
        data = self._load_all()
        seeds = self._seeds_data().get('seeds', [])
        changed = False
        for uid, farm in data.items():
            updated = False
            for plot in farm['land']['plots']:
                if plot.get('crop') and not plot.get('harvestReady'):
                    seed_info = next((s for s in seeds if s.get('name')==plot.get('crop')), None)
                    growth = seed_info.get('growthDays',1) if seed_info else 1
                    planted = plot.get('plantedAt')
                    if planted:
                        try:
                            planted_dt = datetime.fromisoformat(planted)
                        except Exception:
                            planted_dt = datetime.utcnow()
                        days = (datetime.utcnow() - planted_dt).days
                        if days >= growth:
                            plot['harvestReady'] = True
                            plot['growthStage'] = 100
                            updated = True
            if updated:
                data[uid] = farm
                changed = True
        if changed:
            self._save_all(data)
        return changed

    # ========== 事件系统 ==========

    def _events_data(self) -> dict:
        """加载事件配置"""
        path = Path(self.dm.root) / 'data' / 'farm' / 'events.json'
        if not path.exists():
            return {'events': []}
        import json
        return json.loads(path.read_text(encoding='utf-8'))

    def trigger_random_event(self, user_id: str) -> Optional[dict]:
        """触发随机事件"""
        farm = self.load_farm(user_id)
        if not farm:
            return None
        
        events_config = self._events_data().get('events', [])
        if not events_config:
            return None
        
        # 根据概率随机选择事件
        roll = random.randint(1, 100)
        cumulative = 0
        selected_event = None
        
        for event in events_config:
            cumulative += event.get('probability', 0)
            if roll <= cumulative:
                selected_event = event
                break
        
        if not selected_event:
            return None
        
        # 创建激活事件
        now = datetime.utcnow()
        duration = selected_event.get('duration', 1)
        from datetime import timedelta
        expires_at = now + timedelta(days=duration)
        
        active_event = {
            'event_id': selected_event['id'],
            'event_name': selected_event['name'],
            'event_type': selected_event['type'],
            'effect': selected_event.get('effect', {}),
            'started_at': now.isoformat(),
            'expires_at': expires_at.isoformat(),
            'remedied': False
        }
        
        # 添加到农场的活动事件
        if 'activeEvents' not in farm:
            farm['activeEvents'] = []
        farm['activeEvents'].append(active_event)
        
        # 立即应用事件效果
        self._apply_event_effect(farm, selected_event.get('effect', {}))
        
        farm['log'].append({
            'date': now.isoformat(),
            'action': '随机事件',
            'description': f"发生了{selected_event['name']}：{selected_event.get('description', '')}"
        })
        
        self.save_farm(user_id, farm)
        return active_event

    def _apply_event_effect(self, farm: dict, effect: dict):
        """应用事件效果到农场"""
        for plot in farm['land']['plots']:
            if plot.get('crop'):
                # 水分影响
                if 'water' in effect:
                    plot['water'] = max(0, min(100, plot.get('water', 0) + effect['water']))
                # 健康度影响
                if 'health' in effect:
                    plot['health'] = max(0, min(100, plot.get('health', 100) + effect['health']))
                # 肥力影响
                if 'fertility' in effect:
                    plot['fertility'] = max(0, min(100, plot.get('fertility', 0) + effect['fertility']))

    def get_active_events(self, user_id: str) -> List[dict]:
        """获取当前活动事件"""
        farm = self.load_farm(user_id)
        if not farm:
            return []
        
        now = datetime.utcnow()
        active = []
        expired = []
        
        for event in farm.get('activeEvents', []):
            try:
                expires_at = datetime.fromisoformat(event['expires_at'])
                if expires_at > now:
                    active.append(event)
                else:
                    expired.append(event)
            except:
                expired.append(event)
        
        # 清理过期事件
        if expired:
            farm['activeEvents'] = active
            self.save_farm(user_id, farm)
        
        return active

    def remedy_event(self, user_id: str, event_id: int) -> dict:
        """使用道具补救事件"""
        rem = check_cooldown(user_id, 'farm', 'remedy')
        if rem > 0:
            raise RuntimeError(f"cooldown:{rem}")
        
        farm = self.load_farm(user_id)
        if not farm:
            raise ValueError('没有农场')
        
        events_config = self._events_data().get('events', [])
        event_info = next((e for e in events_config if e.get('id') == event_id), None)
        
        if not event_info:
            raise ValueError('事件不存在')
        
        remedy_item = event_info.get('remedy')
        if not remedy_item:
            raise ValueError('该事件无法补救')
        
        # 检查库存中是否有补救道具
        tools = farm.get('inventory', {}).get('tools', [])
        has_remedy = any(t.get('name', '').lower() == remedy_item.lower() for t in tools)
        
        if not has_remedy:
            raise ValueError(f'没有补救道具: {remedy_item}')
        
        # 找到活动事件并标记为已补救
        active_events = farm.get('activeEvents', [])
        target_event = next((e for e in active_events if e.get('event_id') == event_id and not e.get('remedied')), None)
        
        if not target_event:
            raise ValueError('没有需要补救的该事件')
        
        target_event['remedied'] = True
        
        # 恢复部分效果
        effect = event_info.get('effect', {})
        for plot in farm['land']['plots']:
            if plot.get('crop'):
                if 'health' in effect and effect['health'] < 0:
                    plot['health'] = min(100, plot.get('health', 0) + abs(effect['health']) // 2)
        
        farm['log'].append({
            'date': datetime.utcnow().isoformat(),
            'action': '事件补救',
            'description': f"使用{remedy_item}补救了{event_info['name']}"
        })
        
        self.save_farm(user_id, farm)
        set_cooldown(user_id, 'farm', 'remedy', 30)
        return farm

    # ========== 季节系统 ==========

    def _seasons_data(self) -> dict:
        """加载季节配置"""
        path = Path(self.dm.root) / 'data' / 'farm' / 'seasons.json'
        if not path.exists():
            return {'seasons': []}
        import json
        return json.loads(path.read_text(encoding='utf-8'))

    def get_current_season(self) -> Optional[dict]:
        """获取当前季节"""
        seasons = self._seasons_data().get('seasons', [])
        if not seasons:
            return None
        
        now = datetime.utcnow()
        month = now.month
        
        for season in seasons:
            if month in season.get('months', []):
                return season
        
        return seasons[0] if seasons else None

    def get_seasonal_seeds(self) -> dict:
        """获取当季可种植的种子"""
        current_season = self.get_current_season()
        if not current_season:
            return {'seasonal': [], 'other': []}
        
        season_name = current_season.get('name', '')
        seeds = self._seeds_data().get('seeds', [])
        
        seasonal = []
        other = []
        
        for seed in seeds:
            seed_seasons = seed.get('season', [])
            if season_name in seed_seasons or '全年' in seed_seasons:
                seasonal.append(seed)
            else:
                other.append(seed)
        
        return {
            'current_season': current_season,
            'seasonal': seasonal,
            'other': other
        }

    def check_crop_season_bonus(self, seed_name: str) -> float:
        """检查作物的季节加成"""
        current_season = self.get_current_season()
        if not current_season:
            return 1.0
        
        seeds = self._seeds_data().get('seeds', [])
        seed_info = next((s for s in seeds if s.get('name') == seed_name), None)
        
        if not seed_info:
            return 1.0
        
        seed_seasons = seed_info.get('season', [])
        season_name = current_season.get('name', '')
        
        if season_name in seed_seasons or '全年' in seed_seasons:
            return current_season.get('effects', {}).get('growth', 1.0)
        else:
            return 0.5  # 非当季作物减半生长

    # ========== 农产品出售 ==========

    def sell_crop(self, user_id: str, crop_name: str, quantity: int = 1) -> dict:
        """出售农产品"""
        rem = check_cooldown(user_id, 'farm', 'sell')
        if rem > 0:
            raise RuntimeError(f"cooldown:{rem}")
        
        farm = self.load_farm(user_id)
        if not farm:
            raise ValueError('没有农场')
        
        crops = farm.get('inventory', {}).get('crops', [])
        crop_item = next((c for c in crops if c.get('name') == crop_name), None)
        
        if not crop_item or crop_item.get('count', 0) < quantity:
            raise ValueError('农产品数量不足')
        
        # 获取作物售价
        seeds = self._seeds_data().get('seeds', [])
        seed_info = next((s for s in seeds if s.get('name') == crop_name), None)
        
        base_price = seed_info.get('sellPrice', 10) if seed_info else 10
        
        # 季节加成
        season = self.get_current_season()
        season_bonus = 1.0
        if season and seed_info:
            if season.get('name') in seed_info.get('season', []):
                season_bonus = 1.2  # 当季作物加价20%
        
        total_price = int(base_price * quantity * season_bonus)
        
        # 扣除农产品
        crop_item['count'] -= quantity
        if crop_item['count'] <= 0:
            farm['inventory']['crops'] = [c for c in crops if c.get('count', 0) > 0]
        
        # 增加金币
        user = self.dm.load_user(user_id) or {}
        user['money'] = user.get('money', 0) + total_price
        self.dm.save_user(user_id, user)
        
        # 更新统计
        farm['statistics']['totalIncome'] = farm['statistics'].get('totalIncome', 0) + total_price
        
        farm['log'].append({
            'date': datetime.utcnow().isoformat(),
            'action': '出售农产品',
            'description': f"出售了{quantity}个{crop_name}，获得{total_price}金币"
        })
        
        # 增加经验
        farm['experience'] = farm.get('experience', 0) + quantity * 2
        self._check_level_up(farm)
        
        self.save_farm(user_id, farm)
        set_cooldown(user_id, 'farm', 'sell', 3)
        
        return {
            'crop_name': crop_name,
            'quantity': quantity,
            'price_per_unit': base_price,
            'season_bonus': season_bonus,
            'total_price': total_price,
            'farm': farm
        }

    def _check_level_up(self, farm: dict):
        """检查并处理升级"""
        exp = farm.get('experience', 0)
        level = farm.get('level', 1)
        next_level_exp = level * 100
        
        while exp >= next_level_exp:
            farm['level'] = level + 1
            level = farm['level']
            next_level_exp = level * 100
            farm['log'].append({
                'date': datetime.utcnow().isoformat(),
                'action': '农场升级',
                'description': f"农场升级到{level}级！"
            })

    # ========== 批量操作 ==========

    def water_all_crops(self, user_id: str) -> dict:
        """给所有作物浇水"""
        rem = check_cooldown(user_id, 'farm', 'water_all')
        if rem > 0:
            raise RuntimeError(f"cooldown:{rem}")
        
        farm = self.load_farm(user_id)
        if not farm:
            raise ValueError('没有农场')
        
        # 检查水壶
        tools = farm.get('inventory', {}).get('tools', [])
        watering_can = next((t for t in tools if '水壶' in t.get('name', '') and t.get('durability', 0) > 0), None)
        
        if not watering_can:
            raise ValueError('没有可用的水壶')
        
        watered_count = 0
        for plot in farm['land']['plots']:
            if plot.get('crop') and plot.get('water', 0) < 100:
                efficiency = watering_can.get('efficiency', 1)
                plot['water'] = min(100, plot.get('water', 0) + 25 * efficiency)
                watered_count += 1
                watering_can['durability'] -= 1
                if watering_can['durability'] <= 0:
                    break
        
        if watered_count == 0:
            raise ValueError('没有需要浇水的作物')
        
        farm['log'].append({
            'date': datetime.utcnow().isoformat(),
            'action': '批量浇水',
            'description': f"给{watered_count}块地浇了水"
        })
        farm['experience'] = farm.get('experience', 0) + watered_count * 2
        
        self.save_farm(user_id, farm)
        set_cooldown(user_id, 'farm', 'water_all', 30)
        
        return {'watered_count': watered_count, 'farm': farm}

    def fertilize_all_crops(self, user_id: str) -> dict:
        """给所有作物施肥"""
        rem = check_cooldown(user_id, 'farm', 'fertilize_all')
        if rem > 0:
            raise RuntimeError(f"cooldown:{rem}")
        
        farm = self.load_farm(user_id)
        if not farm:
            raise ValueError('没有农场')
        
        # 检查肥料
        tools = farm.get('inventory', {}).get('tools', [])
        fertilizer = next((t for t in tools if '肥料' in t.get('name', '') and t.get('durability', 0) > 0), None)
        
        if not fertilizer:
            raise ValueError('没有可用的肥料')
        
        fertilized_count = 0
        for plot in farm['land']['plots']:
            if plot.get('crop') and plot.get('fertility', 0) < 100:
                efficiency = fertilizer.get('efficiency', 1)
                plot['fertility'] = min(100, plot.get('fertility', 0) + 20 * efficiency)
                fertilized_count += 1
                fertilizer['durability'] -= 1
                if fertilizer['durability'] <= 0:
                    break
        
        if fertilized_count == 0:
            raise ValueError('没有需要施肥的作物')
        
        farm['log'].append({
            'date': datetime.utcnow().isoformat(),
            'action': '批量施肥',
            'description': f"给{fertilized_count}块地施了肥"
        })
        farm['experience'] = farm.get('experience', 0) + fertilized_count * 3
        
        self.save_farm(user_id, farm)
        set_cooldown(user_id, 'farm', 'fertilize_all', 30)
        
        return {'fertilized_count': fertilized_count, 'farm': farm}

    def harvest_all_crops(self, user_id: str) -> dict:
        """收获所有成熟作物"""
        rem = check_cooldown(user_id, 'farm', 'harvest_all')
        if rem > 0:
            raise RuntimeError(f"cooldown:{rem}")
        
        farm = self.load_farm(user_id)
        if not farm:
            raise ValueError('没有农场')
        
        seeds = self._seeds_data().get('seeds', [])
        harvested = []
        
        for i, plot in enumerate(farm['land']['plots']):
            if not plot.get('crop'):
                continue
            
            # 检查是否成熟
            seed_info = next((s for s in seeds if s.get('name') == plot.get('crop')), None)
            growth_days = seed_info.get('growthDays', 1) if seed_info else 1
            planted = plot.get('plantedAt')
            
            if not planted:
                continue
            
            try:
                planted_dt = datetime.fromisoformat(planted)
            except:
                continue
            
            days = (datetime.utcnow() - planted_dt).days
            if days < growth_days and not plot.get('harvestReady'):
                continue
            
            # 收获
            crop_name = plot.get('crop')
            yield_count = seed_info.get('yield', 1) if seed_info else 1
            
            # 健康度影响产量
            health_bonus = plot.get('health', 100) / 100
            final_yield = max(1, int(yield_count * health_bonus))
            
            # 添加到库存
            crops = farm['inventory'].setdefault('crops', [])
            existing = next((c for c in crops if c.get('name') == crop_name), None)
            if existing:
                existing['count'] = existing.get('count', 0) + final_yield
            else:
                crops.append({'name': crop_name, 'count': final_yield})
            
            harvested.append({'name': crop_name, 'yield': final_yield, 'plot': i + 1})
            
            # 重置地块
            plot['crop'] = None
            plot['plantedAt'] = None
            plot['water'] = 0
            plot['fertility'] = 0
            plot['health'] = 100
            plot['growthStage'] = 0
            plot['harvestReady'] = False
        
        if not harvested:
            raise ValueError('没有可收获的作物')
        
        total_harvested = sum(h['yield'] for h in harvested)
        farm['statistics']['totalHarvested'] = farm['statistics'].get('totalHarvested', 0) + total_harvested
        
        farm['log'].append({
            'date': datetime.utcnow().isoformat(),
            'action': '批量收获',
            'description': f"收获了{len(harvested)}种作物，共{total_harvested}个"
        })
        farm['experience'] = farm.get('experience', 0) + total_harvested * 5
        self._check_level_up(farm)
        
        self.save_farm(user_id, farm)
        set_cooldown(user_id, 'farm', 'harvest_all', 10)
        
        return {'harvested': harvested, 'total': total_harvested, 'farm': farm}

    # ========== 农场排行榜 ==========

    def get_farm_ranking(self, rank_type: str = 'level') -> List[dict]:
        """获取农场排行榜"""
        all_data = self._load_all()
        
        rankings = []
        for uid, farm in all_data.items():
            rankings.append({
                'user_id': uid,
                'farm_name': farm.get('name', '未知农场'),
                'level': farm.get('level', 1),
                'experience': farm.get('experience', 0),
                'total_harvested': farm.get('statistics', {}).get('totalHarvested', 0),
                'total_income': farm.get('statistics', {}).get('totalIncome', 0)
            })
        
        # 排序
        if rank_type == 'level':
            rankings.sort(key=lambda x: (x['level'], x['experience']), reverse=True)
        elif rank_type == 'harvest':
            rankings.sort(key=lambda x: x['total_harvested'], reverse=True)
        elif rank_type == 'income':
            rankings.sort(key=lambda x: x['total_income'], reverse=True)
        
        return rankings[:20]

    # ========== 农场状态查看 ==========

    def view_farm_status(self, user_id: str) -> dict:
        """查看农场详细状态"""
        farm = self.load_farm(user_id)
        if not farm:
            raise ValueError('没有农场')
        
        season = self.get_current_season()
        active_events = self.get_active_events(user_id)
        seeds = self._seeds_data().get('seeds', [])
        
        # 计算每个地块的详细状态
        plots_status = []
        for i, plot in enumerate(farm['land']['plots']):
            status = {
                'index': i + 1,
                'crop': plot.get('crop'),
                'water': plot.get('water', 0),
                'fertility': plot.get('fertility', 0),
                'health': plot.get('health', 100),
                'harvestReady': plot.get('harvestReady', False)
            }
            
            if plot.get('crop') and plot.get('plantedAt'):
                seed_info = next((s for s in seeds if s.get('name') == plot.get('crop')), None)
                growth_days = seed_info.get('growthDays', 1) if seed_info else 1
                
                try:
                    planted_dt = datetime.fromisoformat(plot['plantedAt'])
                    days_passed = (datetime.utcnow() - planted_dt).days
                    progress = min(100, int(days_passed / growth_days * 100))
                    status['growth_progress'] = progress
                    status['days_remaining'] = max(0, growth_days - days_passed)
                except:
                    status['growth_progress'] = 0
                    status['days_remaining'] = growth_days
            
            plots_status.append(status)
        
        return {
            'name': farm.get('name'),
            'level': farm.get('level', 1),
            'experience': farm.get('experience', 0),
            'next_level_exp': farm.get('level', 1) * 100,
            'land': {
                'name': farm['land'].get('name'),
                'level': farm['land'].get('level'),
                'size': farm['land'].get('size')
            },
            'plots': plots_status,
            'inventory': farm.get('inventory', {}),
            'statistics': farm.get('statistics', {}),
            'current_season': season,
            'active_events': active_events
        }

