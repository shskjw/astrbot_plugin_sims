from pathlib import Path
import random
import json
from typing import Optional, List, Dict, Any
from datetime import datetime

from ..common.data_manager import DataManager
from ..common.cooldown import check_cooldown, set_cooldown
from .models import (
    Fish, FishingRod, FishingBait, FishBasket, CaughtFish,
    FishingUserData, FishingResult, SellResult, FishingRankingEntry,
    EquipmentShopItem
)


class FishingLogic:
    def __init__(self, data_manager: Optional[DataManager] = None):
        self.dm = data_manager or DataManager()
        self.data_path = Path(self.dm.root) / 'data' / 'fishing'
        self.data_path.mkdir(parents=True, exist_ok=True)
        
        # 缓存配置
        self._fish_data: List[dict] = []
        self._equipment: Dict[str, List[dict]] = {}
        
        # 加载配置
        self._load_configs()

    # ========== 配置加载 ==========
    def _load_configs(self):
        """加载配置文件"""
        self._fish_data = self._load_json_config('fish.json', self._get_default_fish())
        self._equipment = self._load_json_config('equipment.json', self._get_default_equipment())

    def _load_json_config(self, filename: str, default: Any) -> Any:
        """加载JSON配置"""
        p = self.data_path / filename
        if p.exists():
            try:
                return json.loads(p.read_text(encoding='utf-8'))
            except:
                pass
        p.write_text(json.dumps(default, ensure_ascii=False, indent=2), encoding='utf-8')
        return default

    def _get_default_fish(self) -> List[dict]:
        """默认鱼类配置"""
        return [
            {"id": "fish_01", "name": "鲫鱼", "rarity": 1, "price": 10, "weight_min": 0.3, "weight_max": 1.5, "exp": 10, "difficulty": 1, "freshness": 3600},
            {"id": "fish_02", "name": "草鱼", "rarity": 1, "price": 15, "weight_min": 0.5, "weight_max": 3.0, "exp": 15, "difficulty": 1, "freshness": 3600},
            {"id": "fish_03", "name": "鲤鱼", "rarity": 2, "price": 25, "weight_min": 0.8, "weight_max": 5.0, "exp": 25, "difficulty": 2, "freshness": 3000},
            {"id": "fish_04", "name": "黑鱼", "rarity": 2, "price": 40, "weight_min": 1.0, "weight_max": 6.0, "exp": 35, "difficulty": 3, "freshness": 2400},
            {"id": "fish_05", "name": "鲈鱼", "rarity": 3, "price": 60, "weight_min": 0.5, "weight_max": 4.0, "exp": 50, "difficulty": 4, "freshness": 2000},
            {"id": "fish_06", "name": "鳜鱼", "rarity": 3, "price": 80, "weight_min": 0.8, "weight_max": 3.5, "exp": 60, "difficulty": 5, "freshness": 1800},
            {"id": "fish_07", "name": "甲鱼", "rarity": 4, "price": 150, "weight_min": 0.5, "weight_max": 2.0, "exp": 100, "difficulty": 6, "freshness": 7200},
            {"id": "fish_08", "name": "中华鲟", "rarity": 5, "price": 500, "weight_min": 5.0, "weight_max": 50.0, "exp": 300, "difficulty": 8, "freshness": 1200},
            {"id": "fish_09", "name": "娃娃鱼", "rarity": 5, "price": 800, "weight_min": 1.0, "weight_max": 10.0, "exp": 500, "difficulty": 10, "freshness": 900},
        ]

    def _get_default_equipment(self) -> dict:
        """默认装备配置"""
        return {
            "rods": [
                {"id": "rod_01", "name": "竹竿", "level": 1, "success_rate": 40, "price": 0, "upgrade_cost": 100},
                {"id": "rod_02", "name": "碳素竿", "level": 2, "success_rate": 55, "price": 100, "upgrade_cost": 300},
                {"id": "rod_03", "name": "海竿", "level": 3, "success_rate": 70, "price": 300, "upgrade_cost": 600},
                {"id": "rod_04", "name": "专业钓竿", "level": 4, "success_rate": 85, "price": 600, "upgrade_cost": 1000},
                {"id": "rod_05", "name": "大师钓竿", "level": 5, "success_rate": 95, "price": 1000, "upgrade_cost": None}
            ],
            "baits": [
                {"id": "bait_01", "name": "蚯蚓", "level": 1, "attract_rate": 40, "price": 0, "upgrade_cost": 50},
                {"id": "bait_02", "name": "红虫", "level": 2, "attract_rate": 55, "price": 50, "upgrade_cost": 150},
                {"id": "bait_03", "name": "商品饵", "level": 3, "attract_rate": 70, "price": 150, "upgrade_cost": 300},
                {"id": "bait_04", "name": "特制饵料", "level": 4, "attract_rate": 85, "price": 300, "upgrade_cost": 500},
                {"id": "bait_05", "name": "秘制神饵", "level": 5, "attract_rate": 95, "price": 500, "upgrade_cost": None}
            ],
            "baskets": [
                {"id": "basket_01", "name": "简易鱼篓", "capacity": 5, "price": 0},
                {"id": "basket_02", "name": "标准鱼篓", "capacity": 10, "price": 200},
                {"id": "basket_03", "name": "大型鱼篓", "capacity": 20, "price": 500},
                {"id": "basket_04", "name": "保鲜鱼篓", "capacity": 30, "price": 1000},
                {"id": "basket_05", "name": "豪华鱼篓", "capacity": 50, "price": 2000}
            ]
        }

    # ========== 用户数据管理 ==========
    def _users_file(self) -> Path:
        return self.data_path / 'users.json'

    def _ranking_file(self) -> Path:
        return self.data_path / 'ranking.json'

    def _load_users(self) -> dict:
        p = self._users_file()
        if not p.exists():
            return {}
        return json.loads(p.read_text(encoding='utf-8'))

    def _save_users(self, data: dict):
        p = self._users_file()
        p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')

    def _load_ranking(self) -> dict:
        p = self._ranking_file()
        if not p.exists():
            return {}
        return json.loads(p.read_text(encoding='utf-8'))

    def _save_ranking(self, data: dict):
        p = self._ranking_file()
        p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')

    def _get_user_data(self, user_id: str) -> FishingUserData:
        """获取用户钓鱼数据"""
        users = self._load_users()
        if user_id in users:
            return FishingUserData(**users[user_id])
        # 初始化新用户
        data = FishingUserData(user_id=user_id)
        users[user_id] = data.dict()
        self._save_users(users)
        return data

    def _save_user_data(self, user_id: str, data: FishingUserData):
        """保存用户钓鱼数据"""
        users = self._load_users()
        users[user_id] = data.dict()
        self._save_users(users)

    def _get_equipment(self, eq_type: str, eq_id: str) -> Optional[dict]:
        """获取装备信息"""
        items = self._equipment.get(eq_type + 's', [])
        return next((i for i in items if i['id'] == eq_id), None)

    def _get_fish_info(self, fish_id: str) -> Optional[dict]:
        """获取鱼类信息"""
        return next((f for f in self._fish_data if f['id'] == fish_id), None)

    # ========== 核心功能 ==========
    def start_fishing(self, user_id: str) -> dict:
        """开始钓鱼"""
        rem = check_cooldown(user_id, 'fishing', 'start')
        if rem > 0:
            raise RuntimeError(f"cooldown:{rem}")
        
        data = self._get_user_data(user_id)
        
        if data.fishing_status != "idle":
            raise ValueError("你已经在钓鱼了！使用【收杆】来收取鱼获。")
        
        # 检查鱼篓容量
        basket = self._get_equipment('basket', data.basket)
        capacity = basket.get('capacity', 10) if basket else 10
        if len(data.fish_basket) >= capacity:
            raise ValueError("鱼篓已满！请先使用【出售鱼获】清空鱼篓。")
        
        # 设置状态
        data.fishing_status = "waiting"
        data.start_time = datetime.now().timestamp()
        self._save_user_data(user_id, data)
        
        # 计算等待时间
        rod = self._get_equipment('rod', data.rod)
        bait = self._get_equipment('bait', data.bait)
        base_wait = 30  # 基础等待30秒
        
        # 装备减少等待时间
        if rod:
            base_wait -= (rod.get('level', 1) - 1) * 3
        if bait:
            base_wait -= (bait.get('level', 1) - 1) * 2
        
        wait_time = max(10, base_wait) + random.randint(0, 20)
        
        set_cooldown(user_id, 'fishing', 'start', 30)
        
        return {
            "status": "waiting",
            "wait_time": wait_time,
            "message": f"你开始钓鱼了，耐心等待鱼儿上钩...预计需要约 {wait_time} 秒"
        }

    def check_fishing_status(self, user_id: str) -> dict:
        """检查钓鱼状态"""
        data = self._get_user_data(user_id)
        
        if data.fishing_status == "idle":
            return {"status": "idle", "message": "你还没有开始钓鱼"}
        
        elapsed = datetime.now().timestamp() - data.start_time
        
        if data.fishing_status == "waiting":
            # 计算预期等待时间
            rod = self._get_equipment('rod', data.rod)
            bait = self._get_equipment('bait', data.bait)
            base_wait = 30
            if rod:
                base_wait -= (rod.get('level', 1) - 1) * 3
            if bait:
                base_wait -= (bait.get('level', 1) - 1) * 2
            
            if elapsed >= max(10, base_wait):
                # 转为ready状态
                data.fishing_status = "ready"
                self._save_user_data(user_id, data)
                return {"status": "ready", "message": "鱼儿上钩了！快使用【收杆】！"}
            
            remaining = int(max(10, base_wait) - elapsed)
            return {"status": "waiting", "message": f"还在等待中...约 {remaining} 秒后可能有鱼上钩"}
        
        return {"status": data.fishing_status, "message": "鱼儿上钩了！快使用【收杆】！"}

    def pull_rod(self, user_id: str) -> FishingResult:
        """收杆"""
        rem = check_cooldown(user_id, 'fishing', 'pull')
        if rem > 0:
            raise RuntimeError(f"cooldown:{rem}")
        
        data = self._get_user_data(user_id)
        
        if data.fishing_status == "idle":
            raise ValueError("你还没有开始钓鱼！请先使用【开始钓鱼】。")
        
        # 检查是否足够时间
        elapsed = datetime.now().timestamp() - data.start_time
        rod = self._get_equipment('rod', data.rod)
        bait = self._get_equipment('bait', data.bait)
        base_wait = 30
        if rod:
            base_wait -= (rod.get('level', 1) - 1) * 3
        if bait:
            base_wait -= (bait.get('level', 1) - 1) * 2
        
        min_wait = max(10, base_wait)
        
        if data.fishing_status == "waiting" and elapsed < min_wait:
            # 太早收杆
            data.fishing_status = "idle"
            data.start_time = 0
            self._save_user_data(user_id, data)
            set_cooldown(user_id, 'fishing', 'pull', 5)
            return FishingResult(
                success=False,
                message="收杆太早了！鱼儿还没上钩呢..."
            )
        
        # 计算成功率
        rod_rate = rod.get('success_rate', 50) if rod else 50
        bait_rate = bait.get('attract_rate', 50) if bait else 50
        success_rate = (rod_rate + bait_rate) / 2
        
        # 等级加成
        success_rate += data.level * 2
        success_rate = min(95, success_rate)
        
        is_success = random.random() * 100 <= success_rate
        
        result = FishingResult(success=is_success)
        
        if is_success:
            # 筛选可钓到的鱼
            possible_fish = [f for f in self._fish_data if f.get('difficulty', 1) <= data.level]
            if not possible_fish:
                possible_fish = self._fish_data[:3]  # 至少有基础的鱼
            
            # 根据稀有度加权随机
            weights = [max(1, 10 - f.get('rarity', 1) * 2) for f in possible_fish]
            fish_info = random.choices(possible_fish, weights=weights, k=1)[0]
            
            # 计算重量
            weight_min = fish_info.get('weight_min', 0.5)
            weight_max = fish_info.get('weight_max', 2.0)
            weight = round(weight_min + random.random() * (weight_max - weight_min), 2)
            
            # 创建钓到的鱼
            caught = CaughtFish(
                fish_id=fish_info['id'],
                weight=weight,
                catch_time=datetime.now().isoformat(),
                price=int(fish_info.get('price', 10) * weight)
            )
            data.fish_basket.append(caught)
            
            # 更新统计
            data.total_catch += 1
            data.total_weight += weight
            exp_gain = fish_info.get('exp', 10)
            data.exp += exp_gain
            
            # 检查升级
            level_up = False
            exp_needed = data.level * 100
            if data.exp >= exp_needed:
                data.level += 1
                data.exp -= exp_needed
                level_up = True
            
            # 更新排行榜
            ranking = self._load_ranking()
            if user_id not in ranking:
                ranking[user_id] = {
                    "total_catch": 0,
                    "total_weight": 0,
                    "best_catch_fish": None,
                    "best_catch_weight": 0
                }
            ranking[user_id]["total_catch"] += 1
            ranking[user_id]["total_weight"] = round(ranking[user_id]["total_weight"] + weight, 2)
            if weight > ranking[user_id].get("best_catch_weight", 0):
                ranking[user_id]["best_catch_fish"] = fish_info['id']
                ranking[user_id]["best_catch_weight"] = weight
            self._save_ranking(ranking)
            
            result.fish = Fish(**fish_info)
            result.weight = weight
            result.exp_gained = exp_gain
            result.level_up = level_up
            result.new_level = data.level if level_up else 0
            result.message = f"钓到了 {fish_info['name']}！重量: {weight}kg"
            if level_up:
                result.message += f"\n🎉 钓鱼等级提升到 {data.level} 级！"
        else:
            result.message = "可惜，鱼儿跑掉了..."
        
        # 重置状态
        data.fishing_status = "idle"
        data.start_time = 0
        self._save_user_data(user_id, data)
        
        set_cooldown(user_id, 'fishing', 'pull', 5)
        
        return result

    def check_basket(self, user_id: str) -> dict:
        """查看鱼篓"""
        data = self._get_user_data(user_id)
        basket = self._get_equipment('basket', data.basket)
        capacity = basket.get('capacity', 10) if basket else 10
        
        fish_list = []
        for caught in data.fish_basket:
            fish_info = self._get_fish_info(caught.fish_id)
            if fish_info:
                # 计算新鲜度
                catch_time = datetime.fromisoformat(caught.catch_time)
                elapsed = (datetime.now() - catch_time).total_seconds()
                freshness = fish_info.get('freshness', 3600)
                fresh_percent = max(0, (1 - elapsed / freshness) * 100)
                
                fish_list.append({
                    "name": fish_info['name'],
                    "weight": caught.weight,
                    "rarity": fish_info.get('rarity', 1),
                    "base_price": caught.price,
                    "freshness": round(fresh_percent, 1),
                    "is_spoiled": fresh_percent <= 0
                })
        
        return {
            "basket_name": basket.get('name', '简易鱼篓') if basket else '简易鱼篓',
            "capacity": capacity,
            "used": len(data.fish_basket),
            "fish_list": fish_list
        }

    def sell_fish(self, user_id: str) -> SellResult:
        """出售鱼获"""
        rem = check_cooldown(user_id, 'fishing', 'sell')
        if rem > 0:
            raise RuntimeError(f"cooldown:{rem}")
        
        data = self._get_user_data(user_id)
        
        if not data.fish_basket:
            raise ValueError("鱼篓是空的！")
        
        total_price = 0
        fish_count = 0
        spoiled_count = 0
        
        for caught in data.fish_basket:
            fish_info = self._get_fish_info(caught.fish_id)
            if not fish_info:
                continue
            
            catch_time = datetime.fromisoformat(caught.catch_time)
            elapsed = (datetime.now() - catch_time).total_seconds()
            freshness = fish_info.get('freshness', 3600)
            
            if elapsed > freshness:
                spoiled_count += 1
                continue
            
            # 新鲜度影响价格
            fresh_mult = max(0.5, 1 - elapsed / freshness)
            price = int(caught.price * fresh_mult)
            total_price += price
            fish_count += 1
        
        # 清空鱼篓
        data.fish_basket = []
        self._save_user_data(user_id, data)
        
        # 给用户加钱
        user = self.dm.load_user(user_id) or {}
        user['money'] = user.get('money', 0) + total_price
        self.dm.save_user(user_id, user)
        
        set_cooldown(user_id, 'fishing', 'sell', 10)
        
        message = f"出售完成！获得 {total_price} 金币"
        if spoiled_count > 0:
            message += f"\n有 {spoiled_count} 条鱼因不新鲜被丢弃了"
        
        return SellResult(
            total_price=total_price,
            fish_count=fish_count,
            spoiled_count=spoiled_count,
            message=message
        )

    def upgrade_rod(self, user_id: str) -> dict:
        """升级鱼竿"""
        rem = check_cooldown(user_id, 'fishing', 'upgrade')
        if rem > 0:
            raise RuntimeError(f"cooldown:{rem}")
        
        data = self._get_user_data(user_id)
        current_rod = self._get_equipment('rod', data.rod)
        
        if not current_rod or not current_rod.get('upgrade_cost'):
            raise ValueError("当前鱼竿已经是最高级了！")
        
        upgrade_cost = current_rod['upgrade_cost']
        
        user = self.dm.load_user(user_id) or {}
        if user.get('money', 0) < upgrade_cost:
            raise ValueError(f"金币不足！需要 {upgrade_cost} 金币")
        
        # 找到下一级鱼竿
        rods = self._equipment.get('rods', [])
        next_rod = next((r for r in rods if r.get('level') == current_rod['level'] + 1), None)
        
        if not next_rod:
            raise ValueError("没有更高级的鱼竿了！")
        
        user['money'] -= upgrade_cost
        data.rod = next_rod['id']
        
        self.dm.save_user(user_id, user)
        self._save_user_data(user_id, data)
        
        set_cooldown(user_id, 'fishing', 'upgrade', 30)
        
        return {
            "old_rod": current_rod['name'],
            "new_rod": next_rod['name'],
            "cost": upgrade_cost,
            "success_rate": next_rod['success_rate'],
            "message": f"成功升级到 {next_rod['name']}！成功率提升到 {next_rod['success_rate']}%"
        }

    def upgrade_bait(self, user_id: str) -> dict:
        """升级鱼饵"""
        rem = check_cooldown(user_id, 'fishing', 'upgrade_bait')
        if rem > 0:
            raise RuntimeError(f"cooldown:{rem}")
        
        data = self._get_user_data(user_id)
        current_bait = self._get_equipment('bait', data.bait)
        
        if not current_bait or not current_bait.get('upgrade_cost'):
            raise ValueError("当前鱼饵已经是最高级了！")
        
        upgrade_cost = current_bait['upgrade_cost']
        
        user = self.dm.load_user(user_id) or {}
        if user.get('money', 0) < upgrade_cost:
            raise ValueError(f"金币不足！需要 {upgrade_cost} 金币")
        
        baits = self._equipment.get('baits', [])
        next_bait = next((b for b in baits if b.get('level') == current_bait['level'] + 1), None)
        
        if not next_bait:
            raise ValueError("没有更高级的鱼饵了！")
        
        user['money'] -= upgrade_cost
        data.bait = next_bait['id']
        
        self.dm.save_user(user_id, user)
        self._save_user_data(user_id, data)
        
        set_cooldown(user_id, 'fishing', 'upgrade_bait', 30)
        
        return {
            "old_bait": current_bait['name'],
            "new_bait": next_bait['name'],
            "cost": upgrade_cost,
            "attract_rate": next_bait['attract_rate'],
            "message": f"成功升级到 {next_bait['name']}！吸引率提升到 {next_bait['attract_rate']}%"
        }

    def get_equipment_shop(self) -> List[dict]:
        """获取装备商店"""
        shop = []
        
        for rod in self._equipment.get('rods', []):
            if rod.get('price', 0) > 0:
                shop.append({
                    "id": rod['id'],
                    "name": rod['name'],
                    "type": "鱼竿",
                    "price": rod['price'],
                    "attributes": f"成功率: {rod.get('success_rate', 50)}%"
                })
        
        for bait in self._equipment.get('baits', []):
            if bait.get('price', 0) > 0:
                shop.append({
                    "id": bait['id'],
                    "name": bait['name'],
                    "type": "鱼饵",
                    "price": bait['price'],
                    "attributes": f"吸引率: {bait.get('attract_rate', 50)}%"
                })
        
        for basket in self._equipment.get('baskets', []):
            if basket.get('price', 0) > 0:
                shop.append({
                    "id": basket['id'],
                    "name": basket['name'],
                    "type": "鱼篓",
                    "price": basket['price'],
                    "attributes": f"容量: {basket.get('capacity', 10)}"
                })
        
        return shop

    def buy_equipment(self, user_id: str, equipment_id: str) -> dict:
        """购买装备"""
        rem = check_cooldown(user_id, 'fishing', 'buy')
        if rem > 0:
            raise RuntimeError(f"cooldown:{rem}")
        
        # 查找装备
        item = None
        item_type = None
        for eq_type in ['rods', 'baits', 'baskets']:
            items = self._equipment.get(eq_type, [])
            found = next((i for i in items if i['id'] == equipment_id), None)
            if found:
                item = found
                item_type = eq_type
                break
        
        if not item:
            raise ValueError("未找到该装备！")
        
        price = item.get('price', 0)
        if price <= 0:
            raise ValueError("该装备无法购买！")
        
        user = self.dm.load_user(user_id) or {}
        if user.get('money', 0) < price:
            raise ValueError(f"金币不足！需要 {price} 金币")
        
        data = self._get_user_data(user_id)
        
        # 检查是否已拥有
        if item_type == 'rods' and data.rod == equipment_id:
            raise ValueError("你已经拥有这把鱼竿了！")
        if item_type == 'baits' and data.bait == equipment_id:
            raise ValueError("你已经拥有这种鱼饵了！")
        if item_type == 'baskets' and data.basket == equipment_id:
            raise ValueError("你已经拥有这个鱼篓了！")
        
        user['money'] -= price
        
        if item_type == 'rods':
            data.rod = equipment_id
        elif item_type == 'baits':
            data.bait = equipment_id
        elif item_type == 'baskets':
            data.basket = equipment_id
        
        self.dm.save_user(user_id, user)
        self._save_user_data(user_id, data)
        
        set_cooldown(user_id, 'fishing', 'buy', 10)
        
        return {
            "name": item['name'],
            "type": item_type[:-1],  # 去掉s
            "price": price,
            "message": f"成功购买 {item['name']}！"
        }

    def get_fishing_info(self, user_id: str) -> dict:
        """获取钓鱼信息"""
        data = self._get_user_data(user_id)
        rod = self._get_equipment('rod', data.rod)
        bait = self._get_equipment('bait', data.bait)
        basket = self._get_equipment('basket', data.basket)
        
        return {
            "level": data.level,
            "exp": data.exp,
            "exp_needed": data.level * 100,
            "total_catch": data.total_catch,
            "total_weight": round(data.total_weight, 2),
            "rod": rod.get('name', '竹竿') if rod else '竹竿',
            "rod_rate": rod.get('success_rate', 50) if rod else 50,
            "bait": bait.get('name', '蚯蚓') if bait else '蚯蚓',
            "bait_rate": bait.get('attract_rate', 50) if bait else 50,
            "basket": basket.get('name', '简易鱼篓') if basket else '简易鱼篓',
            "basket_capacity": basket.get('capacity', 5) if basket else 5,
            "basket_used": len(data.fish_basket),
            "status": data.fishing_status
        }

    def get_fishing_ranking(self, sort_by: str = "catch") -> List[FishingRankingEntry]:
        """获取钓鱼排行榜"""
        ranking = self._load_ranking()
        users = self._load_users()
        
        entries = []
        for uid, rank_data in ranking.items():
            user = self.dm.load_user(uid) or {}
            user_fishing = users.get(uid, {})
            
            best_fish_name = None
            if rank_data.get('best_catch_fish'):
                fish_info = self._get_fish_info(rank_data['best_catch_fish'])
                best_fish_name = fish_info.get('name') if fish_info else None
            
            entries.append(FishingRankingEntry(
                user_id=uid,
                user_name=user.get('name', f'用户{uid[:6]}'),
                level=user_fishing.get('level', 1),
                total_catch=rank_data.get('total_catch', 0),
                total_weight=rank_data.get('total_weight', 0),
                best_catch_fish=best_fish_name,
                best_catch_weight=rank_data.get('best_catch_weight', 0)
            ))
        
        # 排序
        if sort_by == "weight":
            entries.sort(key=lambda x: x.total_weight, reverse=True)
        elif sort_by == "best":
            entries.sort(key=lambda x: x.best_catch_weight, reverse=True)
        else:  # catch
            entries.sort(key=lambda x: x.total_catch, reverse=True)
        
        return entries[:20]

    def get_fish_list(self) -> List[dict]:
        """获取鱼类图鉴"""
        return [
            {
                "name": f['name'],
                "rarity": f.get('rarity', 1),
                "price": f.get('price', 10),
                "difficulty": f.get('difficulty', 1),
                "weight_range": f"{f.get('weight_min', 0.5)}-{f.get('weight_max', 2.0)}kg"
            }
            for f in self._fish_data
        ]

    # ========== 兼容旧接口 ==========
    def _fish_file(self):
        return self.data_path / 'fish.json'

    def _load_fish(self):
        return self._fish_data

    def go_fishing(self, user_id: str) -> dict:
        """兼容旧的钓鱼接口"""
        # 自动开始并收杆
        data = self._get_user_data(user_id)
        
        if data.fishing_status == "idle":
            self.start_fishing(user_id)
            # 模拟立即上钩
            data = self._get_user_data(user_id)
            data.fishing_status = "ready"
            data.start_time = datetime.now().timestamp() - 100
            self._save_user_data(user_id, data)
        
        result = self.pull_rod(user_id)
        
        if result.success and result.fish:
            return {
                "id": result.fish.id,
                "name": result.fish.name,
                "rarity": result.fish.rarity,
                "weight": result.weight
            }
        else:
            raise ValueError(result.message)

    def fish_shop(self):
        """兼容旧的商店接口"""
        return self._fish_data