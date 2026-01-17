import json
import random
from pathlib import Path
from typing import Optional, Dict, List
from datetime import datetime, timedelta
from ..common.data_manager import DataManager
from ..common.cooldown import check_cooldown, set_cooldown
from . import models

class TavernLogic:
    def __init__(self, data_manager: Optional[DataManager] = None):
        self.dm = data_manager or DataManager()
        self.data_path = Path(self.dm.root) / 'data' / 'tavern'
        self.data_path.mkdir(parents=True, exist_ok=True)

    def _tavern_file(self, user_id: str):
        """获取用户酒馆数据文件路径"""
        return self.data_path / f"{user_id}_tavern.json"

    def _load_tavern_data(self, user_id: str) -> Optional[models.TavernData]:
        """加载用户酒馆数据"""
        p = self._tavern_file(user_id)
        if not p.exists():
            return None
        import json
        data = json.loads(p.read_text(encoding='utf-8'))
        return models.TavernData(**data)

    def _save_tavern_data(self, user_id: str, tavern: models.TavernData):
        """保存用户酒馆数据"""
        p = self._tavern_file(user_id)
        p.write_text(tavern.model_dump_json(), encoding='utf-8')

    def _load_global_drinks(self) -> List[models.Drink]:
        """加载全局饮品数据库"""
        p = self.data_path.parent / 'tavern_drinks.json'
        if not p.exists():
            return []
        import json
        data = json.loads(p.read_text(encoding='utf-8'))
        return [models.Drink(**d) for d in data.get('defaultDrinks', [])]

    def _load_market_items(self) -> List[models.MarketItem]:
        """加载市场物资"""
        p = self.data_path.parent / 'tavern_market.json'
        if not p.exists():
            return []
        import json
        data = json.loads(p.read_text(encoding='utf-8'))
        return [models.MarketItem(**d) for d in data.get('marketItems', [])]

    def create_tavern(self, user_id: str, tavern_name: str, user_money: int) -> Dict:
        """创建酒馆"""
        if self._load_tavern_data(user_id):
            raise ValueError("你已经拥有一家酒馆了！")
        
        initial_cost = 5000
        if user_money < initial_cost:
            raise ValueError(f"创建酒馆需要{initial_cost}元资金，你的资金不足！")
        
        tavern = models.TavernData(
            user_id=user_id,
            name=tavern_name,
            created_at=datetime.now().isoformat(),
            supplies=models.TavernSupplies(beer_basic=20, wine_table=10, spirits_vodka=5)
        )
        
        self._save_tavern_data(user_id, tavern)
        
        user = self.dm.load_user(user_id) or {}
        user['money'] = user.get('money', 0) - initial_cost
        self.dm.save_user(user_id, user)
        
        return {"success": True, "tavern": tavern, "cost": initial_cost}

    def get_tavern_info(self, user_id: str) -> Dict:
        """获取酒馆信息"""
        tavern = self._load_tavern_data(user_id)
        if not tavern:
            raise ValueError("你还没有酒馆！")
        
        total_drinks = sum(d.count for d in tavern.drinks)
        return {
            "tavern": tavern,
            "total_drinks": total_drinks,
            "staff_count": len(tavern.staff)
        }

    def list_drinks(self) -> List[models.Drink]:
        """列出所有可用饮品"""
        return self._load_global_drinks()

    def order_drink(self, user_id: str, drink_id: str) -> Dict:
        """点一杯饮品（消费）"""
        rem = check_cooldown(user_id, 'tavern', 'order')
        if rem > 0:
            raise RuntimeError(f"cooldown:{rem}")
        
        drinks = self.list_drinks()
        drink = next((d for d in drinks if d.id == drink_id), None)
        if not drink:
            raise ValueError('饮品不存在')
        
        user = self.dm.load_user(user_id) or {}
        if user.get('money', 0) < drink.base_price:
            raise ValueError('金币不足')
        
        user['money'] = user.get('money', 0) - drink.base_price
        self.dm.save_user(user_id, user)
        set_cooldown(user_id, 'tavern', 'order', 3)
        
        return {"success": True, "drink": drink, "cost": drink.base_price}

    def list_market_items(self) -> List[models.MarketItem]:
        """列出市场物资"""
        return self._load_market_items()

    def buy_supplies(self, user_id: str, item_id: str, quantity: int, user_money: int) -> Dict:
        """购买酒馆物资"""
        rem = check_cooldown(user_id, 'tavern', 'buy')
        if rem > 0:
            raise RuntimeError(f"cooldown:{rem}")
        
        tavern = self._load_tavern_data(user_id)
        if not tavern:
            raise ValueError("你还没有酒馆！")
        
        market_items = self.list_market_items()
        item = next((i for i in market_items if i.id == item_id), None)
        if not item:
            raise ValueError("未找到该物资！")
        
        if item.quantity < quantity:
            raise ValueError(f"市场库存不足！当前仅有{item.quantity}份该物资。")
        
        total_price = item.price * quantity
        if user_money < total_price:
            raise ValueError(f"你的资金不足！购买{quantity}份{item.name}需要{total_price}元。")
        
        # 更新库存
        supply_attr = item.type + '_' + ['basic', 'craft', 'premium'][item.quality - 1]
        if hasattr(tavern.supplies, supply_attr):
            setattr(tavern.supplies, supply_attr, getattr(tavern.supplies, supply_attr) + quantity)
        
        self._save_tavern_data(user_id, tavern)
        
        user = self.dm.load_user(user_id) or {}
        user['money'] = user.get('money', 0) - total_price
        self.dm.save_user(user_id, user)
        
        set_cooldown(user_id, 'tavern', 'buy', 3)
        
        return {"success": True, "item": item, "quantity": quantity, "total_price": total_price}

    def add_custom_menu_item(self, user_id: str, drink_id: str, price: int) -> Dict:
        """添加自定义菜单项"""
        rem = check_cooldown(user_id, 'tavern', 'menu')
        if rem > 0:
            raise RuntimeError(f"cooldown:{rem}")
        
        tavern = self._load_tavern_data(user_id)
        if not tavern:
            raise ValueError("你还没有酒馆！")
        
        drinks = self.list_drinks()
        drink = next((d for d in drinks if d.id == drink_id), None)
        if not drink:
            raise ValueError('饮品不存在')
        
        max_items = 10 + (tavern.level - 1) * 2
        if len(tavern.custom_menu) >= max_items:
            raise ValueError(f"菜单已满！当前等级最多提供{max_items}种饮品。")
        
        menu_item = {
            "id": drink_id,
            "name": drink.name,
            "price": price,
            "original_price": drink.base_price,
            "added_at": datetime.now().isoformat()
        }
        tavern.custom_menu.append(menu_item)
        self._save_tavern_data(user_id, tavern)
        
        set_cooldown(user_id, 'tavern', 'menu', 2)
        
        return {"success": True, "menu_item": menu_item}

    def operate_tavern(self, user_id: str) -> Dict:
        """营业酒馆（获取每日收入）"""
        rem = check_cooldown(user_id, 'tavern', 'operate')
        if rem > 0:
            raise RuntimeError(f"cooldown:{rem}")
        
        tavern = self._load_tavern_data(user_id)
        if not tavern:
            raise ValueError("你还没有酒馆！")
        
        if not tavern.custom_menu:
            raise ValueError("你的酒馆菜单是空的！请先添加饮品。")
        
        has_supplies = (tavern.supplies.beer_basic + tavern.supplies.wine_table + tavern.supplies.spirits_vodka) >= 2
        if not has_supplies:
            raise ValueError("酒馆缺少必要的物资，请前往市场购买！")
        
        today = datetime.now().date().isoformat()
        if tavern.last_operated:
            last_date = datetime.fromisoformat(tavern.last_operated).date().isoformat()
            if last_date == today:
                raise ValueError("今天已经营业过了，请明天再来！")
        
        # 计算客流量
        base_customers = int(tavern.popularity * (0.9 + random.random() * 0.2))
        customers = min(base_customers, tavern.capacity)
        
        # 计算平均消费
        avg_consumption = 30 + (tavern.level - 1) * 5
        avg_consumption *= (0.8 + tavern.reputation * 0.04)
        avg_consumption *= (0.8 + tavern.atmosphere / 250)
        avg_consumption *= (0.8 + tavern.cleanliness / 500)
        avg_consumption *= (0.9 + random.random() * 0.2)
        
        income = int(customers * avg_consumption)
        staff_salary = sum(s.salary for s in tavern.staff)
        profit = income - staff_salary
        
        # 消耗物资
        tavern.supplies.beer_basic = max(0, tavern.supplies.beer_basic - int(customers / 10))
        tavern.supplies.wine_table = max(0, tavern.supplies.wine_table - int(customers / 15))
        tavern.supplies.spirits_vodka = max(0, tavern.supplies.spirits_vodka - int(customers / 20))
        
        # 更新酒馆数据
        tavern.last_operated = datetime.now().isoformat()
        tavern.daily_income = profit
        tavern.total_income += profit
        tavern.cleanliness = max(0, tavern.cleanliness - 15)
        
        if tavern.cleanliness < 30:
            tavern.reputation = max(1, tavern.reputation - 1)
        
        self._save_tavern_data(user_id, tavern)
        
        user = self.dm.load_user(user_id) or {}
        user['money'] = user.get('money', 0) + profit
        self.dm.save_user(user_id, user)
        
        set_cooldown(user_id, 'tavern', 'operate', 5)
        
        return {
            "success": True,
            "customers": customers,
            "avg_consumption": round(avg_consumption, 2),
            "income": income,
            "staff_salary": staff_salary,
            "profit": profit,
            "tavern": tavern
        }

    def upgrade_tavern(self, user_id: str, user_money: int) -> Dict:
        """升级酒馆"""
        rem = check_cooldown(user_id, 'tavern', 'upgrade')
        if rem > 0:
            raise RuntimeError(f"cooldown:{rem}")
        
        tavern = self._load_tavern_data(user_id)
        if not tavern:
            raise ValueError("你还没有酒馆！")
        
        if tavern.level >= 10:
            raise ValueError(f"你的酒馆已经达到最高等级(10)了！")
        
        upgrade_cost = 5000 * (2 ** (tavern.level - 1))
        
        if user_money < upgrade_cost:
            raise ValueError(f"升级酒馆到{tavern.level + 1}级需要{upgrade_cost}元，你的资金不足！")
        
        prev_capacity = tavern.capacity
        tavern.level += 1
        tavern.capacity += 10
        tavern.atmosphere += 5
        tavern.reputation = min(10, tavern.reputation + 1)
        
        self._save_tavern_data(user_id, tavern)
        
        user = self.dm.load_user(user_id) or {}
        user['money'] = user.get('money', 0) - upgrade_cost
        self.dm.save_user(user_id, user)
        
        set_cooldown(user_id, 'tavern', 'upgrade', 5)
        
        return {
            "success": True,
            "prev_capacity": prev_capacity,
            "capacity_increase": tavern.capacity - prev_capacity,
            "upgrade_cost": upgrade_cost,
            "tavern": tavern
        }

    def hire_staff(self, user_id: str, staff_type: str, user_money: int) -> Dict:
        """雇佣员工"""
        rem = check_cooldown(user_id, 'tavern', 'hire')
        if rem > 0:
            raise RuntimeError(f"cooldown:{rem}")
        
        tavern = self._load_tavern_data(user_id)
        if not tavern:
            raise ValueError("你还没有酒馆！")
        
        staff_types = {
            "bartender": {"name": "酒保", "salary": 100, "level_req": 1},
            "waiter": {"name": "服务员", "salary": 80, "level_req": 1},
            "cleaner": {"name": "清洁工", "salary": 60, "level_req": 2},
            "security": {"name": "保安", "salary": 120, "level_req": 3},
            "musician": {"name": "驻唱歌手", "salary": 200, "level_req": 4}
        }
        
        if staff_type not in staff_types:
            raise ValueError(f"未知的员工类型: {staff_type}")
        
        info = staff_types[staff_type]
        
        if tavern.level < info["level_req"]:
            raise ValueError(f"雇佣{info['name']}需要酒馆等级达到{info['level_req']}级！")
        
        if any(s.staff_type == staff_type for s in tavern.staff):
            raise ValueError(f"你已经雇佣了{info['name']}！同类型员工只能雇佣一名。")
        
        max_staff = min(5, tavern.level)
        if len(tavern.staff) >= max_staff:
            raise ValueError(f"酒馆员工已达上限({max_staff}名)！")
        
        hire_cost = info["salary"] * 5
        if user_money < hire_cost:
            raise ValueError(f"雇佣{info['name']}需要{hire_cost}元，你的资金不足！")
        
        surnames = ['王', '李', '张', '刘', '陈', '杨', '赵', '黄', '周', '吴']
        names = ['明', '芳', '军', '华', '超', '燕', '娜', '强', '玲', '杰']
        staff_name = random.choice(surnames) + random.choice(names)
        
        staff = models.Staff(
            id=f"staff_{int(datetime.now().timestamp() * 1000)}",
            name=staff_name,
            staff_type=staff_type,
            salary=info["salary"],
            hired_at=datetime.now().isoformat()
        )
        
        tavern.staff.append(staff)
        self._save_tavern_data(user_id, tavern)
        
        user = self.dm.load_user(user_id) or {}
        user['money'] = user.get('money', 0) - hire_cost
        self.dm.save_user(user_id, user)
        
        set_cooldown(user_id, 'tavern', 'hire', 5)
        
        return {"success": True, "staff": staff, "hire_cost": hire_cost}

    def fire_staff(self, user_id: str, staff_id: str) -> Dict:
        """解雇员工"""
        rem = check_cooldown(user_id, 'tavern', 'fire')
        if rem > 0:
            raise RuntimeError(f"cooldown:{rem}")
        
        tavern = self._load_tavern_data(user_id)
        if not tavern:
            raise ValueError("你还没有酒馆！")
        
        staff_idx = next((i for i, s in enumerate(tavern.staff) if s.id == staff_id), -1)
        if staff_idx == -1:
            raise ValueError(f"未找到ID为{staff_id}的员工！")
        
        fired_staff = tavern.staff.pop(staff_idx)
        self._save_tavern_data(user_id, tavern)
        
        set_cooldown(user_id, 'tavern', 'fire', 5)
        
        return {"success": True, "fired_staff": fired_staff}

    # ========== 高级功能：事件系统 ==========
    
    def _load_events(self) -> List[Dict]:
        """加载事件数据"""
        p = self.data_path / 'tavern_events.json'
        if not p.exists():
            p = self.data_path.parent / 'tavern' / 'tavern_events.json'
        if not p.exists():
            return []
        data = json.loads(p.read_text(encoding='utf-8'))
        return data.get('events', [])
    
    def trigger_random_event(self, user_id: str) -> Optional[Dict]:
        """触发随机事件（营业时调用）"""
        tavern = self._load_tavern_data(user_id)
        if not tavern:
            return None
        
        events = self._load_events()
        if not events:
            return None
        
        # 筛选符合等级要求的事件
        eligible_events = [e for e in events if e.get('minLevel', 1) <= tavern.level]
        if not eligible_events:
            return None
        
        # 30%概率触发事件
        if random.random() > 0.3:
            return None
        
        # 按频率权重选择事件
        total_freq = sum(e.get('frequency', 10) for e in eligible_events)
        roll = random.random() * total_freq
        cumulative = 0
        selected_event = None
        
        for event in eligible_events:
            cumulative += event.get('frequency', 10)
            if roll <= cumulative:
                selected_event = event
                break
        
        if not selected_event:
            selected_event = random.choice(eligible_events)
        
        return selected_event
    
    def process_event_choice(self, user_id: str, event_id: str, choice_idx: int) -> Dict:
        """处理事件选择"""
        rem = check_cooldown(user_id, 'tavern', 'event')
        if rem > 0:
            raise RuntimeError(f"cooldown:{rem}")
        
        tavern = self._load_tavern_data(user_id)
        if not tavern:
            raise ValueError("你还没有酒馆！")
        
        events = self._load_events()
        event = next((e for e in events if e['id'] == event_id), None)
        if not event:
            raise ValueError("事件不存在！")
        
        choices = event.get('choices', [])
        if choice_idx < 0 or choice_idx >= len(choices):
            raise ValueError("无效的选择！")
        
        choice = choices[choice_idx]
        effects = choice.get('effects', {})
        requirements = choice.get('requirements', {})
        
        # 检查需求
        if 'staff' in requirements:
            required_staff = requirements['staff']
            has_staff = any(s.staff_type in required_staff for s in tavern.staff)
            if not has_staff:
                raise ValueError(f"需要员工类型: {', '.join(required_staff)}")
        
        if 'level' in requirements:
            if tavern.level < requirements['level']:
                raise ValueError(f"需要酒馆等级: {requirements['level']}")
        
        # 应用效果
        applied_effects = {}
        
        if 'popularity' in effects:
            change = effects['popularity']
            tavern.popularity = max(1, min(100, tavern.popularity + change))
            applied_effects['popularity'] = change
        
        if 'reputation' in effects:
            change = effects['reputation']
            tavern.reputation = max(1, min(10, tavern.reputation + change))
            applied_effects['reputation'] = change
        
        if 'customerSatisfaction' in effects:
            change = effects['customerSatisfaction']
            tavern.customer_satisfaction = max(0, min(100, tavern.customer_satisfaction + change))
            applied_effects['customer_satisfaction'] = change
        
        if 'cleanliness' in effects:
            change = effects['cleanliness']
            tavern.cleanliness = max(0, min(100, tavern.cleanliness + change))
            applied_effects['cleanliness'] = change
        
        if 'income' in effects:
            income = effects['income']
            user = self.dm.load_user(user_id) or {}
            user['money'] = user.get('money', 0) + income
            self.dm.save_user(user_id, user)
            applied_effects['income'] = income
        
        if 'costs' in effects:
            cost = effects['costs']
            user = self.dm.load_user(user_id) or {}
            if user.get('money', 0) < cost:
                raise ValueError(f"资金不足！需要{cost}元")
            user['money'] = user.get('money', 0) - cost
            self.dm.save_user(user_id, user)
            applied_effects['costs'] = cost
        
        # 记录事件
        tavern.special_events.append({
            'event_id': event_id,
            'title': event['title'],
            'choice': choice['text'],
            'effects': applied_effects,
            'time': datetime.now().isoformat()
        })
        
        # 只保留最近10条事件记录
        if len(tavern.special_events) > 10:
            tavern.special_events = tavern.special_events[-10:]
        
        self._save_tavern_data(user_id, tavern)
        set_cooldown(user_id, 'tavern', 'event', 10)
        
        return {
            "success": True,
            "event": event,
            "choice": choice,
            "effects": applied_effects,
            "tavern": tavern
        }
    
    def get_pending_event(self, user_id: str) -> Optional[Dict]:
        """获取待处理的事件（上次营业触发的）"""
        # 从用户数据或缓存获取
        p = self.data_path / f"{user_id}_pending_event.json"
        if not p.exists():
            return None
        data = json.loads(p.read_text(encoding='utf-8'))
        return data
    
    def set_pending_event(self, user_id: str, event: Optional[Dict]):
        """设置待处理事件"""
        p = self.data_path / f"{user_id}_pending_event.json"
        if event is None:
            if p.exists():
                p.unlink()
        else:
            p.write_text(json.dumps(event, ensure_ascii=False), encoding='utf-8')
    
    def list_available_events(self, user_id: str) -> List[Dict]:
        """列出当前等级可触发的事件"""
        tavern = self._load_tavern_data(user_id)
        if not tavern:
            return []
        
        events = self._load_events()
        return [e for e in events if e.get('minLevel', 1) <= tavern.level]
    
    def get_event_history(self, user_id: str) -> List[Dict]:
        """获取事件历史"""
        tavern = self._load_tavern_data(user_id)
        if not tavern:
            return []
        return tavern.special_events
    
    # ========== 高级功能：排行榜系统 ==========
    
    def _get_all_taverns(self) -> List[Dict]:
        """获取所有酒馆数据"""
        taverns = []
        for p in self.data_path.glob("*_tavern.json"):
            try:
                data = json.loads(p.read_text(encoding='utf-8'))
                taverns.append(data)
            except:
                pass
        return taverns
    
    def get_tavern_ranking(self, sort_by: str = 'score') -> List[Dict]:
        """获取酒馆排行榜"""
        taverns = self._get_all_taverns()
        
        # 计算综合评分
        for t in taverns:
            level = t.get('level', 1)
            total_income = t.get('total_income', 0)
            reputation = t.get('reputation', 1)
            staff_count = len(t.get('staff', []))
            popularity = t.get('popularity', 10)
            
            # 综合评分公式
            score = (level * 1000) + (total_income // 100) + (reputation * 500) + (staff_count * 200) + (popularity * 10)
            t['rank_score'] = score
        
        # 排序
        if sort_by == 'income':
            taverns.sort(key=lambda x: x.get('total_income', 0), reverse=True)
        elif sort_by == 'level':
            taverns.sort(key=lambda x: x.get('level', 1), reverse=True)
        elif sort_by == 'reputation':
            taverns.sort(key=lambda x: x.get('reputation', 1), reverse=True)
        else:  # 默认按综合评分
            taverns.sort(key=lambda x: x.get('rank_score', 0), reverse=True)
        
        # 添加排名
        rankings = []
        for i, t in enumerate(taverns[:20], 1):  # 只返回前20名
            rankings.append({
                'rank': i,
                'user_id': t.get('user_id', 'unknown'),
                'name': t.get('name', '未知酒馆'),
                'level': t.get('level', 1),
                'total_income': t.get('total_income', 0),
                'reputation': t.get('reputation', 1),
                'staff_count': len(t.get('staff', [])),
                'rank_score': t.get('rank_score', 0)
            })
        
        return rankings
    
    def get_my_rank(self, user_id: str) -> Optional[Dict]:
        """获取我的排名"""
        rankings = self.get_tavern_ranking()
        for r in rankings:
            if r['user_id'] == user_id:
                return r
        
        # 如果不在前20名，单独计算
        tavern = self._load_tavern_data(user_id)
        if not tavern:
            return None
        
        all_taverns = self._get_all_taverns()
        for t in all_taverns:
            level = t.get('level', 1)
            total_income = t.get('total_income', 0)
            reputation = t.get('reputation', 1)
            staff_count = len(t.get('staff', []))
            popularity = t.get('popularity', 10)
            t['rank_score'] = (level * 1000) + (total_income // 100) + (reputation * 500) + (staff_count * 200) + (popularity * 10)
        
        all_taverns.sort(key=lambda x: x.get('rank_score', 0), reverse=True)
        
        my_rank = next((i+1 for i, t in enumerate(all_taverns) if t.get('user_id') == user_id), None)
        if not my_rank:
            return None
        
        my_score = (tavern.level * 1000) + (tavern.total_income // 100) + (tavern.reputation * 500) + (len(tavern.staff) * 200) + (tavern.popularity * 10)
        
        return {
            'rank': my_rank,
            'user_id': user_id,
            'name': tavern.name,
            'level': tavern.level,
            'total_income': tavern.total_income,
            'reputation': tavern.reputation,
            'staff_count': len(tavern.staff),
            'rank_score': my_score
        }
    
    # ========== 高级功能：参观系统 ==========
    
    def visit_tavern(self, visitor_id: str, owner_id: str) -> Dict:
        """参观其他玩家的酒馆"""
        rem = check_cooldown(visitor_id, 'tavern', 'visit')
        if rem > 0:
            raise RuntimeError(f"cooldown:{rem}")
        
        if visitor_id == owner_id:
            raise ValueError("不能参观自己的酒馆！")
        
        # 检查参观者是否有酒馆
        visitor_tavern = self._load_tavern_data(visitor_id)
        if not visitor_tavern:
            raise ValueError("你需要先拥有酒馆才能参观他人！")
        
        # 加载目标酒馆
        target_tavern = self._load_tavern_data(owner_id)
        if not target_tavern:
            raise ValueError("目标玩家没有酒馆！")
        
        # 增加目标酒馆人气
        target_tavern.popularity = min(100, target_tavern.popularity + 1)
        
        # 参观者获得灵感（随机属性小幅提升）
        inspiration_bonus = random.choice(['atmosphere', 'cleanliness'])
        if inspiration_bonus == 'atmosphere':
            visitor_tavern.atmosphere = min(100, visitor_tavern.atmosphere + 2)
        else:
            visitor_tavern.cleanliness = min(100, visitor_tavern.cleanliness + 5)
        
        self._save_tavern_data(owner_id, target_tavern)
        self._save_tavern_data(visitor_id, visitor_tavern)
        
        set_cooldown(visitor_id, 'tavern', 'visit', 60)  # 60秒冷却
        
        return {
            "success": True,
            "target_tavern": {
                "name": target_tavern.name,
                "level": target_tavern.level,
                "popularity": target_tavern.popularity,
                "atmosphere": target_tavern.atmosphere,
                "reputation": target_tavern.reputation,
                "menu_count": len(target_tavern.custom_menu),
                "staff_count": len(target_tavern.staff)
            },
            "inspiration_bonus": inspiration_bonus,
            "bonus_amount": 2 if inspiration_bonus == 'atmosphere' else 5
        }
    
    def rate_tavern(self, visitor_id: str, owner_id: str, rating: int, comment: str = "") -> Dict:
        """给酒馆评分"""
        rem = check_cooldown(visitor_id, 'tavern', 'rate')
        if rem > 0:
            raise RuntimeError(f"cooldown:{rem}")
        
        if visitor_id == owner_id:
            raise ValueError("不能给自己的酒馆评分！")
        
        if rating < 1 or rating > 5:
            raise ValueError("评分必须在1-5之间！")
        
        target_tavern = self._load_tavern_data(owner_id)
        if not target_tavern:
            raise ValueError("目标玩家没有酒馆！")
        
        # 加载或创建评分记录文件
        ratings_file = self.data_path / f"{owner_id}_ratings.json"
        if ratings_file.exists():
            ratings_data = json.loads(ratings_file.read_text(encoding='utf-8'))
        else:
            ratings_data = {"ratings": [], "average": 0}
        
        # 添加评分
        ratings_data['ratings'].append({
            "visitor_id": visitor_id,
            "rating": rating,
            "comment": comment,
            "time": datetime.now().isoformat()
        })
        
        # 只保留最近50条评分
        if len(ratings_data['ratings']) > 50:
            ratings_data['ratings'] = ratings_data['ratings'][-50:]
        
        # 计算平均分
        avg = sum(r['rating'] for r in ratings_data['ratings']) / len(ratings_data['ratings'])
        ratings_data['average'] = round(avg, 2)
        
        ratings_file.write_text(json.dumps(ratings_data, ensure_ascii=False, indent=2), encoding='utf-8')
        
        # 高分会提升目标酒馆声誉
        if rating >= 4:
            target_tavern.reputation = min(10, target_tavern.reputation + 0.1)
            self._save_tavern_data(owner_id, target_tavern)
        
        set_cooldown(visitor_id, 'tavern', 'rate', 300)  # 5分钟冷却
        
        return {
            "success": True,
            "rating": rating,
            "new_average": ratings_data['average'],
            "total_ratings": len(ratings_data['ratings'])
        }
    
    def get_tavern_ratings(self, user_id: str) -> Dict:
        """获取酒馆的评分"""
        tavern = self._load_tavern_data(user_id)
        if not tavern:
            raise ValueError("酒馆不存在！")
        
        ratings_file = self.data_path / f"{user_id}_ratings.json"
        if not ratings_file.exists():
            return {
                "tavern_name": tavern.name,
                "average": 0,
                "total_ratings": 0,
                "recent_ratings": []
            }
        
        ratings_data = json.loads(ratings_file.read_text(encoding='utf-8'))
        
        return {
            "tavern_name": tavern.name,
            "average": ratings_data.get('average', 0),
            "total_ratings": len(ratings_data.get('ratings', [])),
            "recent_ratings": ratings_data.get('ratings', [])[-5:]  # 最近5条
        }

    # ========== 高级功能：特殊活动系统 ==========
    
    def _get_activities_config(self) -> List[Dict]:
        """获取活动配置"""
        return [
            {
                "id": "happy_hour",
                "name": "欢乐时光",
                "type": "promotion",
                "description": "饮品全场8折，吸引更多顾客",
                "duration_hours": 2,
                "cost": 200,
                "min_level": 1,
                "effects": {"popularity": 10, "income_bonus": 20}
            },
            {
                "id": "live_music",
                "name": "现场音乐会",
                "type": "entertainment",
                "description": "邀请歌手驻唱，提升氛围",
                "duration_hours": 3,
                "cost": 500,
                "min_level": 2,
                "effects": {"atmosphere": 15, "popularity": 15, "income_bonus": 30},
                "requirements": {"staff": ["musician"]}
            },
            {
                "id": "theme_night",
                "name": "主题之夜",
                "type": "event",
                "description": "举办特殊主题派对",
                "duration_hours": 4,
                "cost": 800,
                "min_level": 3,
                "effects": {"popularity": 20, "reputation": 1, "income_bonus": 50}
            },
            {
                "id": "tasting_event",
                "name": "品鉴会",
                "type": "premium",
                "description": "高端饮品品鉴活动",
                "duration_hours": 2,
                "cost": 1000,
                "min_level": 4,
                "effects": {"reputation": 2, "income_bonus": 80}
            },
            {
                "id": "competition",
                "name": "调酒大赛",
                "type": "competition",
                "description": "举办调酒比赛，吸引酒馆主参加",
                "duration_hours": 3,
                "cost": 1500,
                "min_level": 5,
                "effects": {"popularity": 30, "reputation": 2, "income_bonus": 100}
            }
        ]
    
    def _get_active_activities_file(self) -> Path:
        return self.data_path / 'active_activities.json'
    
    def _load_active_activities(self) -> List[Dict]:
        """加载进行中的活动"""
        p = self._get_active_activities_file()
        if not p.exists():
            return []
        return json.loads(p.read_text(encoding='utf-8'))
    
    def _save_active_activities(self, activities: List[Dict]):
        """保存活动数据"""
        p = self._get_active_activities_file()
        p.write_text(json.dumps(activities, ensure_ascii=False, indent=2), encoding='utf-8')
    
    def list_available_activities(self, user_id: str) -> List[Dict]:
        """列出可举办的活动"""
        tavern = self._load_tavern_data(user_id)
        if not tavern:
            return []
        
        activities = self._get_activities_config()
        available = []
        
        for act in activities:
            if tavern.level >= act['min_level']:
                act_copy = act.copy()
                # 检查需求
                requirements_met = True
                if 'requirements' in act:
                    if 'staff' in act['requirements']:
                        required_staff = act['requirements']['staff']
                        has_staff = any(s.staff_type in required_staff for s in tavern.staff)
                        if not has_staff:
                            requirements_met = False
                            act_copy['missing_requirement'] = f"需要员工: {', '.join(required_staff)}"
                
                act_copy['can_host'] = requirements_met
                available.append(act_copy)
        
        return available
    
    def host_activity(self, user_id: str, activity_id: str) -> Dict:
        """举办活动"""
        rem = check_cooldown(user_id, 'tavern', 'activity')
        if rem > 0:
            raise RuntimeError(f"cooldown:{rem}")
        
        tavern = self._load_tavern_data(user_id)
        if not tavern:
            raise ValueError("你还没有酒馆！")
        
        activities = self._get_activities_config()
        activity = next((a for a in activities if a['id'] == activity_id), None)
        
        if not activity:
            raise ValueError("活动不存在！")
        
        if tavern.level < activity['min_level']:
            raise ValueError(f"举办此活动需要酒馆等级达到{activity['min_level']}级！")
        
        # 检查需求
        if 'requirements' in activity:
            if 'staff' in activity['requirements']:
                required_staff = activity['requirements']['staff']
                has_staff = any(s.staff_type in required_staff for s in tavern.staff)
                if not has_staff:
                    raise ValueError(f"需要员工: {', '.join(required_staff)}")
        
        # 检查资金
        user = self.dm.load_user(user_id) or {}
        if user.get('money', 0) < activity['cost']:
            raise ValueError(f"资金不足！举办{activity['name']}需要{activity['cost']}元")
        
        # 检查是否已有进行中的活动
        active_activities = self._load_active_activities()
        my_active = next((a for a in active_activities if a['host_id'] == user_id), None)
        if my_active:
            raise ValueError("你已经有一个进行中的活动了！")
        
        # 扣费
        user['money'] -= activity['cost']
        self.dm.save_user(user_id, user)
        
        # 创建活动
        now = datetime.now()
        end_time = now + timedelta(hours=activity['duration_hours'])
        
        active_activity = {
            'id': f"activity_{int(now.timestamp() * 1000)}",
            'activity_id': activity_id,
            'activity_name': activity['name'],
            'host_id': user_id,
            'tavern_name': tavern.name,
            'start_time': now.isoformat(),
            'end_time': end_time.isoformat(),
            'effects': activity['effects'],
            'participants': [],
            'bonus_earned': 0
        }
        
        active_activities.append(active_activity)
        self._save_active_activities(active_activities)
        
        # 应用即时效果
        effects = activity['effects']
        if 'popularity' in effects:
            tavern.popularity = min(100, tavern.popularity + effects['popularity'])
        if 'atmosphere' in effects:
            tavern.atmosphere = min(100, tavern.atmosphere + effects['atmosphere'])
        if 'reputation' in effects:
            tavern.reputation = min(10, tavern.reputation + effects['reputation'])
        
        self._save_tavern_data(user_id, tavern)
        
        set_cooldown(user_id, 'tavern', 'activity', 3600)  # 1小时冷却
        
        return {
            "success": True,
            "activity": active_activity,
            "effects_applied": effects,
            "cost": activity['cost']
        }
    
    def join_activity(self, user_id: str, activity_instance_id: str) -> Dict:
        """参加其他酒馆的活动"""
        rem = check_cooldown(user_id, 'tavern', 'join_activity')
        if rem > 0:
            raise RuntimeError(f"cooldown:{rem}")
        
        active_activities = self._load_active_activities()
        activity = next((a for a in active_activities if a['id'] == activity_instance_id), None)
        
        if not activity:
            raise ValueError("活动不存在或已结束！")
        
        if activity['host_id'] == user_id:
            raise ValueError("不能参加自己举办的活动！")
        
        if user_id in activity['participants']:
            raise ValueError("你已经参加了这个活动！")
        
        # 检查是否有酒馆
        my_tavern = self._load_tavern_data(user_id)
        if not my_tavern:
            raise ValueError("你需要先拥有酒馆才能参加活动！")
        
        activity['participants'].append(user_id)
        self._save_active_activities(active_activities)
        
        # 参与者也获得一些加成
        my_tavern.popularity = min(100, my_tavern.popularity + 2)
        self._save_tavern_data(user_id, my_tavern)
        
        set_cooldown(user_id, 'tavern', 'join_activity', 300)
        
        return {
            "success": True,
            "activity_name": activity['activity_name'],
            "host_tavern": activity['tavern_name']
        }
    
    def list_active_activities(self) -> List[Dict]:
        """列出所有进行中的活动"""
        activities = self._load_active_activities()
        now = datetime.now()
        
        # 过滤已结束的活动
        active = []
        for act in activities:
            end_time = datetime.fromisoformat(act['end_time'])
            if now < end_time:
                act['remaining_hours'] = (end_time - now).total_seconds() / 3600
                active.append(act)
        
        return active
    
    def end_expired_activities(self) -> List[Dict]:
        """结束过期的活动（系统调用）"""
        activities = self._load_active_activities()
        now = datetime.now()
        
        ended = []
        remaining = []
        
        for act in activities:
            end_time = datetime.fromisoformat(act['end_time'])
            if now >= end_time:
                ended.append(act)
            else:
                remaining.append(act)
        
        self._save_active_activities(remaining)
        return ended
    
    # ========== 高级功能：合作酿酒系统 ==========
    
    def _get_brewing_file(self) -> Path:
        return self.data_path / 'brewing_projects.json'
    
    def _load_brewing_data(self) -> Dict:
        """加载酿酒数据"""
        p = self._get_brewing_file()
        if not p.exists():
            return {'active': [], 'completed': []}
        return json.loads(p.read_text(encoding='utf-8'))
    
    def _save_brewing_data(self, data: Dict):
        """保存酿酒数据"""
        p = self._get_brewing_file()
        p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    
    def _get_brewing_recipes(self) -> List[Dict]:
        """酿酒配方"""
        return [
            {
                "id": "craft_beer",
                "name": "精酿啤酒",
                "type": "beer",
                "base_quality": 60,
                "brewing_hours": 24,
                "cost": 300,
                "min_participants": 1,
                "max_participants": 3,
                "description": "清爽的精酿啤酒"
            },
            {
                "id": "fruit_wine",
                "name": "水果酒",
                "type": "wine",
                "base_quality": 65,
                "brewing_hours": 48,
                "cost": 500,
                "min_participants": 2,
                "max_participants": 4,
                "description": "甜美的水果发酵酒"
            },
            {
                "id": "aged_whiskey",
                "name": "陈年威士忌",
                "type": "spirits",
                "base_quality": 75,
                "brewing_hours": 72,
                "cost": 1000,
                "min_participants": 2,
                "max_participants": 5,
                "description": "醇厚的陈年烈酒"
            },
            {
                "id": "special_blend",
                "name": "秘制调和酒",
                "type": "special",
                "base_quality": 80,
                "brewing_hours": 96,
                "cost": 2000,
                "min_participants": 3,
                "max_participants": 6,
                "description": "多种原料调和的特殊佳酿"
            }
        ]
    
    def list_brewing_recipes(self) -> List[Dict]:
        """列出酿酒配方"""
        return self._get_brewing_recipes()
    
    def start_brewing(self, user_id: str, recipe_id: str, brew_name: str) -> Dict:
        """发起合作酿酒"""
        rem = check_cooldown(user_id, 'tavern', 'brewing')
        if rem > 0:
            raise RuntimeError(f"cooldown:{rem}")
        
        tavern = self._load_tavern_data(user_id)
        if not tavern:
            raise ValueError("你还没有酒馆！")
        
        recipes = self._get_brewing_recipes()
        recipe = next((r for r in recipes if r['id'] == recipe_id), None)
        
        if not recipe:
            raise ValueError("酿酒配方不存在！")
        
        # 检查资金
        user = self.dm.load_user(user_id) or {}
        if user.get('money', 0) < recipe['cost']:
            raise ValueError(f"资金不足！酿造{recipe['name']}需要{recipe['cost']}元")
        
        # 检查是否有进行中的酿酒项目
        brewing_data = self._load_brewing_data()
        my_brewing = next((b for b in brewing_data['active'] if b['initiator_id'] == user_id), None)
        if my_brewing:
            raise ValueError("你已经有一个进行中的酿酒项目了！")
        
        # 扣费
        user['money'] -= recipe['cost']
        self.dm.save_user(user_id, user)
        
        # 创建酿酒项目
        now = datetime.now()
        complete_time = now + timedelta(hours=recipe['brewing_hours'])
        
        project = {
            'id': f"brew_{int(now.timestamp() * 1000)}",
            'name': brew_name or recipe['name'],
            'recipe_id': recipe_id,
            'recipe_name': recipe['name'],
            'initiator_id': user_id,
            'participants': {
                user_id: {'contributed': True, 'contribution': recipe['cost']}
            },
            'type': recipe['type'],
            'quality': recipe['base_quality'],
            'progress': 0,
            'status': 'brewing',
            'created_time': now.isoformat(),
            'estimated_complete': complete_time.isoformat(),
            'min_participants': recipe['min_participants'],
            'max_participants': recipe['max_participants']
        }
        
        brewing_data['active'].append(project)
        self._save_brewing_data(brewing_data)
        
        set_cooldown(user_id, 'tavern', 'brewing', 1800)  # 30分钟冷却
        
        return {
            "success": True,
            "project": project,
            "cost": recipe['cost'],
            "estimated_hours": recipe['brewing_hours']
        }
    
    def join_brewing(self, user_id: str, project_id: str, contribution: int = 100) -> Dict:
        """参与合作酿酒"""
        rem = check_cooldown(user_id, 'tavern', 'join_brewing')
        if rem > 0:
            raise RuntimeError(f"cooldown:{rem}")
        
        tavern = self._load_tavern_data(user_id)
        if not tavern:
            raise ValueError("你需要有酒馆才能参与酿酒！")
        
        brewing_data = self._load_brewing_data()
        project = next((p for p in brewing_data['active'] if p['id'] == project_id), None)
        
        if not project:
            raise ValueError("酿酒项目不存在！")
        
        if project['initiator_id'] == user_id:
            raise ValueError("不能参与自己发起的项目！")
        
        if user_id in project['participants']:
            raise ValueError("你已经参与了这个项目！")
        
        if len(project['participants']) >= project['max_participants']:
            raise ValueError("该项目参与人数已满！")
        
        # 检查贡献金额
        min_contribution = 100
        if contribution < min_contribution:
            raise ValueError(f"最低贡献金额为{min_contribution}元！")
        
        user = self.dm.load_user(user_id) or {}
        if user.get('money', 0) < contribution:
            raise ValueError("资金不足！")
        
        user['money'] -= contribution
        self.dm.save_user(user_id, user)
        
        # 加入项目
        project['participants'][user_id] = {
            'contributed': True,
            'contribution': contribution
        }
        
        # 贡献提升品质
        quality_bonus = contribution // 50
        project['quality'] = min(100, project['quality'] + quality_bonus)
        
        self._save_brewing_data(brewing_data)
        
        set_cooldown(user_id, 'tavern', 'join_brewing', 300)
        
        return {
            "success": True,
            "project_name": project['name'],
            "contribution": contribution,
            "quality_bonus": quality_bonus,
            "new_quality": project['quality']
        }
    
    def check_brewing_progress(self, project_id: str) -> Dict:
        """检查酿酒进度"""
        brewing_data = self._load_brewing_data()
        project = next((p for p in brewing_data['active'] if p['id'] == project_id), None)
        
        if not project:
            # 检查已完成的
            completed = next((p for p in brewing_data['completed'] if p['id'] == project_id), None)
            if completed:
                return {"status": "completed", "project": completed}
            raise ValueError("酿酒项目不存在！")
        
        now = datetime.now()
        created = datetime.fromisoformat(project['created_time'])
        estimated = datetime.fromisoformat(project['estimated_complete'])
        
        total_hours = (estimated - created).total_seconds() / 3600
        elapsed_hours = (now - created).total_seconds() / 3600
        
        progress = min(100, int(elapsed_hours / total_hours * 100))
        project['progress'] = progress
        
        remaining_hours = max(0, (estimated - now).total_seconds() / 3600)
        
        self._save_brewing_data(brewing_data)
        
        return {
            "status": "brewing",
            "project": project,
            "progress": progress,
            "remaining_hours": round(remaining_hours, 1)
        }
    
    def complete_brewing(self, user_id: str, project_id: str) -> Dict:
        """完成酿酒（领取成品）"""
        brewing_data = self._load_brewing_data()
        project_idx = next((i for i, p in enumerate(brewing_data['active']) if p['id'] == project_id), None)
        
        if project_idx is None:
            raise ValueError("酿酒项目不存在！")
        
        project = brewing_data['active'][project_idx]
        
        if project['initiator_id'] != user_id:
            raise ValueError("只有发起者才能领取成品！")
        
        # 检查是否已完成
        now = datetime.now()
        estimated = datetime.fromisoformat(project['estimated_complete'])
        
        if now < estimated:
            remaining = (estimated - now).total_seconds() / 3600
            raise ValueError(f"酿造还未完成！还需{remaining:.1f}小时")
        
        # 检查参与人数是否足够
        if len(project['participants']) < project['min_participants']:
            raise ValueError(f"参与人数不足！需要至少{project['min_participants']}人")
        
        # 计算最终品质（参与人数加成）
        participant_bonus = (len(project['participants']) - 1) * 5
        final_quality = min(100, project['quality'] + participant_bonus)
        
        # 给发起者添加酿造成品
        tavern = self._load_tavern_data(user_id)
        if tavern:
            product = {
                'id': f"brewed_{project['id']}",
                'drink_id': project['recipe_id'],
                'drink_name': project['name'],
                'quality': final_quality,
                'created_at': now.isoformat(),
                'count': 1 + len(project['participants']) // 2,  # 参与人数越多产量越高
                'brewed': True
            }
            tavern.drinks.append(models.UserDrink(**product))
            self._save_tavern_data(user_id, tavern)
        
        # 给所有参与者增加声望
        for pid in project['participants']:
            p_tavern = self._load_tavern_data(pid)
            if p_tavern:
                p_tavern.reputation = min(10, p_tavern.reputation + 0.5)
                self._save_tavern_data(pid, p_tavern)
        
        # 移动到完成列表
        project['status'] = 'completed'
        project['completed_time'] = now.isoformat()
        project['final_quality'] = final_quality
        
        brewing_data['active'].pop(project_idx)
        brewing_data['completed'].append(project)
        
        # 保留最近20条
        if len(brewing_data['completed']) > 20:
            brewing_data['completed'] = brewing_data['completed'][-20:]
        
        self._save_brewing_data(brewing_data)
        
        return {
            "success": True,
            "product_name": project['name'],
            "quality": final_quality,
            "count": 1 + len(project['participants']) // 2,
            "participant_count": len(project['participants'])
        }
    
    def list_brewing_projects(self) -> List[Dict]:
        """列出所有进行中的酿酒项目"""
        brewing_data = self._load_brewing_data()
        projects = []
        
        now = datetime.now()
        for p in brewing_data['active']:
            estimated = datetime.fromisoformat(p['estimated_complete'])
            created = datetime.fromisoformat(p['created_time'])
            
            total_hours = (estimated - created).total_seconds() / 3600
            elapsed_hours = (now - created).total_seconds() / 3600
            progress = min(100, int(elapsed_hours / total_hours * 100))
            
            projects.append({
                'id': p['id'],
                'name': p['name'],
                'type': p['type'],
                'initiator_id': p['initiator_id'],
                'participant_count': len(p['participants']),
                'max_participants': p['max_participants'],
                'quality': p['quality'],
                'progress': progress,
                'is_complete': now >= estimated
            })
        
        return projects
    
    def get_my_brewing(self, user_id: str) -> List[Dict]:
        """获取我参与的酿酒项目"""
        brewing_data = self._load_brewing_data()
        return [p for p in brewing_data['active'] if user_id in p['participants']]