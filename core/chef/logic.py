from pathlib import Path
import json
import random
from typing import Optional, Dict, List
from datetime import datetime, timedelta
from ..common.data_manager import DataManager
from ..common.cooldown import check_cooldown, set_cooldown
from .models import ChefData, Recipe, Ingredient, Kitchenware, Dish, Team, Contest, MarketListing, CoopCooking, Achievement, ChefTitle


class ChefLogic:
    def __init__(self, data_manager: Optional[DataManager] = None):
        self.dm = data_manager or DataManager()
        self.data_root = Path(self.dm.root) / 'data'
        self.chef_data_dir = self.data_root / 'chef_users'
        self.chef_data_dir.mkdir(parents=True, exist_ok=True)
        
        # 加载全局数据文件
        self.recipes = self._load_json(self.data_root / 'recipes.json', 'recipes')
        self.ingredients = self._load_json(self.data_root / 'ingredients.json', 'ingredients')
        self.kitchenware = self._load_json(self.data_root / 'kitchenware.json', 'kitchenware')
        
    def _load_json(self, path: Path, key: str = None):
        """加载 JSON 文件"""
        if not path.exists():
            return []
        try:
            data = json.loads(path.read_text(encoding='utf-8'))
            return data.get(key, []) if key else data
        except:
            return []
    
    def _get_chef_file(self, user_id: str) -> Path:
        return self.chef_data_dir / f"{user_id}_chef.json"
    
    def _load_chef_data(self, user_id: str) -> Optional[Dict]:
        """加载厨师数据"""
        chef_file = self._get_chef_file(user_id)
        if chef_file.exists():
            return json.loads(chef_file.read_text(encoding='utf-8'))
        return None
    
    def _save_chef_data(self, user_id: str, data: Dict):
        """保存厨师数据"""
        chef_file = self._get_chef_file(user_id)
        chef_file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    
    # ========== 基础厨师操作 ==========
    
    def become_chef(self, user_id: str) -> Dict:
        """成为厨师"""
        chef_data = self._load_chef_data(user_id)
        if chef_data:
            raise ValueError("你已经是厨师了")
        
        new_chef = {
            'level': 1,
            'exp': 0,
            'recipes': ['soup_01'],  # 初始解锁
            'success_count': 0,
            'total_count': 0,
            'reputation': 50,
            'created_time': datetime.now().isoformat()
        }
        self._save_chef_data(user_id, new_chef)
        return new_chef
    
    # ========== 食谱系统 ==========
    
    def list_recipes(self) -> List[Dict]:
        """列出所有食谱"""
        return self.recipes
    
    def learn_recipe(self, user_id: str, recipe_id: str) -> Dict:
        """学习食谱"""
        chef_data = self._load_chef_data(user_id)
        if not chef_data:
            raise ValueError("你还不是厨师")
        
        recipe = next((r for r in self.recipes if r['id'] == recipe_id), None)
        if not recipe:
            raise ValueError("食谱不存在")
        
        if recipe_id in chef_data['recipes']:
            raise ValueError("你已经会这个食谱了")
        
        if chef_data['level'] < recipe['unlockLevel']:
            raise ValueError(f"需要达到等级{recipe['unlockLevel']}才能学习")
        
        # 扣费
        user = self.dm.load_user(user_id) or {'money': 0}
        learn_cost = recipe['difficulty'] * 100
        
        if user.get('money', 0) < learn_cost:
            raise ValueError(f"金币不足，需要{learn_cost}金币")
        
        user['money'] -= learn_cost
        self.dm.save_user(user_id, user)
        
        chef_data['recipes'].append(recipe_id)
        self._save_chef_data(user_id, chef_data)
        
        return {'recipe': recipe, 'cost': learn_cost}
    
    # ========== 烹饪系统 ==========
    
    def cook_dish(self, user_id: str, recipe_id: str) -> Dict:
        """制作料理"""
        # 检查冷却
        rem = check_cooldown(user_id, 'chef', 'cook')
        if rem > 0:
            raise RuntimeError(f"cooldown:{rem}")
        
        chef_data = self._load_chef_data(user_id)
        if not chef_data:
            raise ValueError("你还不是厨师")
        
        recipe = next((r for r in self.recipes if r['id'] == recipe_id), None)
        if not recipe:
            raise ValueError("食谱不存在")
        
        if recipe_id not in chef_data['recipes']:
            raise ValueError("你还没有解锁这个食谱")
        
        user = self.dm.load_user(user_id) or {'money': 0, 'backpack': []}
        
        # 检查食材（简化版，仅检查总数）
        required_count = sum(ing['amount'] for ing in recipe['ingredients'])
        backpack_ingredients = [b for b in user.get('backpack', []) if b.get('type') == 'ingredient']
        if len(backpack_ingredients) < required_count:
            raise ValueError("食材不足")
        
        # 获取厨具加成
        kitchenware_bonus = self._get_kitchenware_bonus(user)
        
        # 计算成功率
        base_success = recipe['successRate']
        level_bonus = chef_data['level'] * 2
        final_success = min(95, base_success + level_bonus + kitchenware_bonus['success_rate_bonus'])
        
        is_success = random.random() * 100 <= final_success
        
        # 更新统计
        chef_data['total_count'] += 1
        if is_success:
            chef_data['success_count'] += 1
            chef_data['exp'] += recipe['exp']
            chef_data['reputation'] += 1
            
            # 检查升级
            while chef_data['exp'] >= chef_data['level'] * 100:
                chef_data['level'] += 1
                chef_data['exp'] -= (chef_data['level'] - 1) * 100
            
            # 获得金币
            dish_price = int(recipe['basePrice'] * (1 + chef_data['reputation'] / 100))
            user['money'] = user.get('money', 0) + dish_price
        
        self._save_chef_data(user_id, chef_data)
        self.dm.save_user(user_id, user)
        
        set_cooldown(user_id, 'chef', 'cook', 30)
        
        return {
            'success': is_success,
            'recipe': recipe,
            'chef_level': chef_data['level'],
            'chef_exp': chef_data['exp']
        }
    
    def _get_kitchenware_bonus(self, user: Dict) -> Dict:
        """获取厨具加成"""
        bonus = {
            'success_rate_bonus': 0,
            'quality_bonus': 0,
            'time_reduction': 0
        }
        
        backpack_kitchenware = [b for b in user.get('backpack', []) if b.get('type') == 'kitchenware']
        for kw in backpack_kitchenware:
            kw_data = next((k for k in self.kitchenware if k['id'] == kw['id']), None)
            if kw_data:
                bonus['success_rate_bonus'] += kw_data.get('successRateBonus', 0)
                bonus['quality_bonus'] += kw_data.get('qualityBonus', 0)
                bonus['time_reduction'] += kw_data.get('timeReduction', 0)
        
        return bonus
    
    # ========== 食材系统 ==========
    
    def list_ingredients(self) -> List[Dict]:
        """列出所有食材"""
        return self.ingredients
    
    def buy_ingredient(self, user_id: str, ingredient_id: str, amount: int = 1) -> Dict:
        """购买食材"""
        ingredient = next((i for i in self.ingredients if i['id'] == ingredient_id), None)
        if not ingredient:
            raise ValueError("食材不存在")
        
        user = self.dm.load_user(user_id) or {'money': 0, 'backpack': []}
        total_cost = ingredient['price'] * amount
        
        if user.get('money', 0) < total_cost:
            raise ValueError(f"金币不足，需要{total_cost}金币")
        
        user['money'] -= total_cost
        
        # 添加到背包
        backpack_item = {
            'id': ingredient_id,
            'name': ingredient['name'],
            'type': 'ingredient',
            'amount': amount
        }
        user['backpack'].append(backpack_item)
        
        self.dm.save_user(user_id, user)
        
        return {'ingredient': ingredient, 'amount': amount, 'cost': total_cost}
    
    # ========== 厨具系统 ==========
    
    def list_kitchenware(self) -> List[Dict]:
        """列出所有厨具"""
        return self.kitchenware
    
    def buy_kitchenware(self, user_id: str, kitchenware_id: str) -> Dict:
        """购买厨具"""
        chef_data = self._load_chef_data(user_id)
        if not chef_data:
            raise ValueError("你还不是厨师")
        
        kw = next((k for k in self.kitchenware if k['id'] == kitchenware_id), None)
        if not kw:
            raise ValueError("厨具不存在")
        
        if chef_data['level'] < kw['unlockLevel']:
            raise ValueError(f"需要达到等级{kw['unlockLevel']}才能购买")
        
        user = self.dm.load_user(user_id) or {'money': 0, 'backpack': []}
        
        if user.get('money', 0) < kw['price']:
            raise ValueError(f"金币不足，需要{kw['price']}金币")
        
        # 检查是否已拥有
        if any(b['id'] == kitchenware_id and b.get('type') == 'kitchenware' for b in user.get('backpack', [])):
            raise ValueError("你已经拥有这个厨具了")
        
        user['money'] -= kw['price']
        user['backpack'].append({
            'id': kitchenware_id,
            'name': kw['name'],
            'type': 'kitchenware'
        })
        
        self.dm.save_user(user_id, user)
        
        return {'kitchenware': kw, 'cost': kw['price']}
    
    # ========== 出售系统 ==========
    
    def sell_dish(self, user_id: str, dish_id: str) -> Dict:
        """出售料理"""
        chef_data = self._load_chef_data(user_id)
        if not chef_data:
            raise ValueError("你还不是厨师")
        
        user = self.dm.load_user(user_id) or {'money': 0, 'backpack': []}
        
        # 从背包找到料理（简化版）
        dish_idx = next((i for i, b in enumerate(user.get('backpack', [])) if b.get('id') == dish_id and b.get('type') == 'dish'), None)
        if dish_idx is None:
            raise ValueError("料理不存在")
        
        dish = user['backpack'][dish_idx]
        # 出售价格=基础价格*（1+声望加成）
        price = int(dish.get('base_price', 20) * (1 + chef_data['reputation'] / 100))
        
        user['money'] = user.get('money', 0) + price
        del user['backpack'][dish_idx]
        
        self.dm.save_user(user_id, user)
        
        return {'dish': dish, 'price': price}
    
    # ========== 统计信息 ==========
    
    def get_chef_info(self, user_id: str) -> Dict:
        """获取厨师信息"""
        chef_data = self._load_chef_data(user_id)
        if not chef_data:
            raise ValueError("你还不是厨师")
        
        success_rate = (chef_data['success_count'] / chef_data['total_count'] * 100 
                       if chef_data['total_count'] > 0 else 0)
        
        return {
            'level': chef_data['level'],
            'exp': chef_data['exp'],
            'recipes_count': len(chef_data['recipes']),
            'success_count': chef_data['success_count'],
            'total_count': chef_data['total_count'],
            'success_rate': f"{success_rate:.1f}%",
            'reputation': chef_data['reputation']
        }

    # ========== 高级功能：团队系统 ==========
    
    def _get_team_file(self) -> Path:
        return self.data_root / 'chef_teams.json'
    
    def _load_teams(self) -> List[Dict]:
        """加载所有团队"""
        p = self._get_team_file()
        if not p.exists():
            return []
        return json.loads(p.read_text(encoding='utf-8'))
    
    def _save_teams(self, teams: List[Dict]):
        """保存团队数据"""
        p = self._get_team_file()
        p.write_text(json.dumps(teams, ensure_ascii=False, indent=2), encoding='utf-8')
    
    def create_team(self, user_id: str, team_name: str) -> Dict:
        """创建厨师团队"""
        rem = check_cooldown(user_id, 'chef', 'team')
        if rem > 0:
            raise RuntimeError(f"cooldown:{rem}")
        
        chef_data = self._load_chef_data(user_id)
        if not chef_data:
            raise ValueError("你还不是厨师！")
        
        if chef_data['level'] < 3:
            raise ValueError("创建团队需要厨师等级达到3级！")
        
        teams = self._load_teams()
        
        # 检查是否已在团队中
        for team in teams:
            if user_id in team['members']:
                raise ValueError(f"你已经在团队「{team['name']}」中了！")
        
        # 检查团队名是否重复
        if any(t['name'] == team_name for t in teams):
            raise ValueError("该团队名已被使用！")
        
        # 检查资金
        user = self.dm.load_user(user_id) or {}
        create_cost = 500
        if user.get('money', 0) < create_cost:
            raise ValueError(f"创建团队需要{create_cost}金币！")
        
        user['money'] -= create_cost
        self.dm.save_user(user_id, user)
        
        # 创建团队
        team = {
            'id': f"team_{int(datetime.now().timestamp() * 1000)}",
            'name': team_name,
            'leader_id': user_id,
            'members': [user_id],
            'level': 1,
            'exp': 0,
            'funds': 0,
            'created_time': datetime.now().isoformat()
        }
        
        teams.append(team)
        self._save_teams(teams)
        
        set_cooldown(user_id, 'chef', 'team', 60)
        
        return {"success": True, "team": team, "cost": create_cost}
    
    def get_user_team(self, user_id: str) -> Optional[Dict]:
        """获取用户所在的团队"""
        teams = self._load_teams()
        for team in teams:
            if user_id in team['members']:
                return team
        return None
    
    def join_team(self, user_id: str, team_id: str) -> Dict:
        """加入团队"""
        rem = check_cooldown(user_id, 'chef', 'team')
        if rem > 0:
            raise RuntimeError(f"cooldown:{rem}")
        
        chef_data = self._load_chef_data(user_id)
        if not chef_data:
            raise ValueError("你还不是厨师！")
        
        teams = self._load_teams()
        
        # 检查是否已在团队
        if self.get_user_team(user_id):
            raise ValueError("你已经在一个团队中了！请先退出当前团队。")
        
        # 找到目标团队
        team = next((t for t in teams if t['id'] == team_id), None)
        if not team:
            raise ValueError("团队不存在！")
        
        if len(team['members']) >= 5:
            raise ValueError("该团队已满员(最多5人)！")
        
        team['members'].append(user_id)
        self._save_teams(teams)
        
        set_cooldown(user_id, 'chef', 'team', 30)
        
        return {"success": True, "team": team}
    
    def leave_team(self, user_id: str) -> Dict:
        """退出团队"""
        teams = self._load_teams()
        team = self.get_user_team(user_id)
        
        if not team:
            raise ValueError("你不在任何团队中！")
        
        if team['leader_id'] == user_id:
            raise ValueError("队长不能直接退出团队！请先转让队长或解散团队。")
        
        # 从团队中移除
        for t in teams:
            if t['id'] == team['id']:
                t['members'].remove(user_id)
                break
        
        self._save_teams(teams)
        
        return {"success": True, "left_team": team['name']}
    
    def disband_team(self, user_id: str) -> Dict:
        """解散团队"""
        teams = self._load_teams()
        team = self.get_user_team(user_id)
        
        if not team:
            raise ValueError("你不在任何团队中！")
        
        if team['leader_id'] != user_id:
            raise ValueError("只有队长才能解散团队！")
        
        if len(team['members']) > 1:
            raise ValueError("团队还有其他成员，请先让他们退出！")
        
        # 删除团队
        teams = [t for t in teams if t['id'] != team['id']]
        self._save_teams(teams)
        
        return {"success": True, "disbanded_team": team['name']}
    
    def get_team_ranking(self) -> List[Dict]:
        """获取团队排行榜"""
        teams = self._load_teams()
        
        # 计算每个团队的综合实力
        for team in teams:
            total_level = 0
            total_reputation = 0
            for member_id in team['members']:
                member_chef = self._load_chef_data(member_id)
                if member_chef:
                    total_level += member_chef['level']
                    total_reputation += member_chef['reputation']
            
            team['total_level'] = total_level
            team['total_reputation'] = total_reputation
            team['power'] = team['level'] * 100 + total_level * 10 + total_reputation
        
        # 按实力排序
        teams.sort(key=lambda x: x.get('power', 0), reverse=True)
        
        rankings = []
        for i, t in enumerate(teams[:20], 1):
            rankings.append({
                'rank': i,
                'id': t['id'],
                'name': t['name'],
                'level': t['level'],
                'member_count': len(t['members']),
                'total_reputation': t['total_reputation'],
                'power': t['power']
            })
        
        return rankings
    
    # ========== 高级功能：比赛系统 ==========
    
    def _get_contest_file(self) -> Path:
        return self.data_root / 'chef_contests.json'
    
    def _load_contests(self) -> Dict:
        """加载比赛数据"""
        p = self._get_contest_file()
        if not p.exists():
            return {'active': [], 'history': []}
        return json.loads(p.read_text(encoding='utf-8'))
    
    def _save_contests(self, data: Dict):
        """保存比赛数据"""
        p = self._get_contest_file()
        p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    
    def create_contest(self, user_id: str, contest_name: str, recipe_id: str) -> Dict:
        """创建厨艺比赛"""
        rem = check_cooldown(user_id, 'chef', 'contest')
        if rem > 0:
            raise RuntimeError(f"cooldown:{rem}")
        
        chef_data = self._load_chef_data(user_id)
        if not chef_data:
            raise ValueError("你还不是厨师！")
        
        if chef_data['level'] < 3:
            raise ValueError("举办比赛需要厨师等级达到3级！")
        
        # 检查食谱
        recipe = next((r for r in self.recipes if r['id'] == recipe_id), None)
        if not recipe:
            raise ValueError("食谱不存在！")
        
        if recipe_id not in chef_data['recipes']:
            raise ValueError("你还没有掌握这个食谱！")
        
        # 检查资金
        user = self.dm.load_user(user_id) or {}
        contest_cost = 300
        if user.get('money', 0) < contest_cost:
            raise ValueError(f"举办比赛需要{contest_cost}金币！")
        
        user['money'] -= contest_cost
        self.dm.save_user(user_id, user)
        
        # 创建比赛
        contest = {
            'id': f"contest_{int(datetime.now().timestamp() * 1000)}",
            'name': contest_name,
            'creator_id': user_id,
            'recipe_id': recipe_id,
            'recipe_name': recipe['name'],
            'participants': {},  # {user_id: {score, submitted_at}}
            'deadline': (datetime.now() + timedelta(hours=24)).isoformat(),
            'status': 'active',
            'created_time': datetime.now().isoformat()
        }
        
        # 创建者自动参加
        contest['participants'][user_id] = {
            'score': 0,
            'submitted': False,
            'joined_at': datetime.now().isoformat()
        }
        
        contests = self._load_contests()
        contests['active'].append(contest)
        self._save_contests(contests)
        
        set_cooldown(user_id, 'chef', 'contest', 3600)  # 1小时冷却
        
        return {"success": True, "contest": contest, "cost": contest_cost}
    
    def join_contest(self, user_id: str, contest_id: str) -> Dict:
        """参加比赛"""
        chef_data = self._load_chef_data(user_id)
        if not chef_data:
            raise ValueError("你还不是厨师！")
        
        contests = self._load_contests()
        contest = next((c for c in contests['active'] if c['id'] == contest_id), None)
        
        if not contest:
            raise ValueError("比赛不存在或已结束！")
        
        if user_id in contest['participants']:
            raise ValueError("你已经参加了这个比赛！")
        
        # 检查是否会食谱
        if contest['recipe_id'] not in chef_data['recipes']:
            raise ValueError(f"你需要先学会「{contest['recipe_name']}」才能参加！")
        
        contest['participants'][user_id] = {
            'score': 0,
            'submitted': False,
            'joined_at': datetime.now().isoformat()
        }
        
        self._save_contests(contests)
        
        return {"success": True, "contest": contest}
    
    def submit_contest_dish(self, user_id: str, contest_id: str) -> Dict:
        """提交比赛作品"""
        rem = check_cooldown(user_id, 'chef', 'submit')
        if rem > 0:
            raise RuntimeError(f"cooldown:{rem}")
        
        chef_data = self._load_chef_data(user_id)
        if not chef_data:
            raise ValueError("你还不是厨师！")
        
        contests = self._load_contests()
        contest = next((c for c in contests['active'] if c['id'] == contest_id), None)
        
        if not contest:
            raise ValueError("比赛不存在或已结束！")
        
        if user_id not in contest['participants']:
            raise ValueError("你还没有参加这个比赛！")
        
        if contest['participants'][user_id]['submitted']:
            raise ValueError("你已经提交过作品了！")
        
        # 计算作品分数（基于厨师等级、声望和随机因素）
        base_score = 50
        level_bonus = chef_data['level'] * 5
        reputation_bonus = chef_data['reputation'] // 10
        random_bonus = random.randint(-10, 20)
        
        total_score = base_score + level_bonus + reputation_bonus + random_bonus
        total_score = max(10, min(100, total_score))  # 限制在10-100
        
        contest['participants'][user_id]['score'] = total_score
        contest['participants'][user_id]['submitted'] = True
        contest['participants'][user_id]['submitted_at'] = datetime.now().isoformat()
        
        self._save_contests(contests)
        set_cooldown(user_id, 'chef', 'submit', 60)
        
        return {"success": True, "score": total_score, "contest": contest}
    
    def end_contest(self, user_id: str, contest_id: str) -> Dict:
        """结束比赛（仅创建者可用）"""
        contests = self._load_contests()
        contest_idx = next((i for i, c in enumerate(contests['active']) if c['id'] == contest_id), None)
        
        if contest_idx is None:
            raise ValueError("比赛不存在或已结束！")
        
        contest = contests['active'][contest_idx]
        
        if contest['creator_id'] != user_id:
            raise ValueError("只有创建者才能结束比赛！")
        
        # 计算排名
        participants = [(uid, data) for uid, data in contest['participants'].items() if data['submitted']]
        participants.sort(key=lambda x: x[1]['score'], reverse=True)
        
        # 发放奖励
        rewards = []
        for rank, (uid, data) in enumerate(participants[:3], 1):
            reward_money = {1: 500, 2: 300, 3: 100}.get(rank, 0)
            reward_exp = {1: 100, 2: 50, 3: 25}.get(rank, 0)
            reward_rep = {1: 10, 2: 5, 3: 2}.get(rank, 0)
            
            # 发放金币
            u = self.dm.load_user(uid) or {}
            u['money'] = u.get('money', 0) + reward_money
            self.dm.save_user(uid, u)
            
            # 增加经验和声望
            chef = self._load_chef_data(uid)
            if chef:
                chef['exp'] += reward_exp
                chef['reputation'] += reward_rep
                self._save_chef_data(uid, chef)
            
            rewards.append({
                'rank': rank,
                'user_id': uid,
                'score': data['score'],
                'reward_money': reward_money,
                'reward_exp': reward_exp,
                'reward_rep': reward_rep
            })
        
        # 移动到历史
        contest['status'] = 'finished'
        contest['finished_time'] = datetime.now().isoformat()
        contest['results'] = rewards
        
        contests['active'].pop(contest_idx)
        contests['history'].append(contest)
        
        # 只保留最近20场历史比赛
        if len(contests['history']) > 20:
            contests['history'] = contests['history'][-20:]
        
        self._save_contests(contests)
        
        return {"success": True, "results": rewards, "contest": contest}
    
    def list_active_contests(self) -> List[Dict]:
        """列出活跃的比赛"""
        contests = self._load_contests()
        return [{
            'id': c['id'],
            'name': c['name'],
            'recipe_name': c['recipe_name'],
            'participant_count': len(c['participants']),
            'deadline': c['deadline'],
            'creator_id': c['creator_id']
        } for c in contests['active']]
    
    # ========== 高级功能：食材市场 ==========
    
    def _get_market_file(self) -> Path:
        return self.data_root / 'chef_market.json'
    
    def _load_market(self) -> Dict:
        """加载市场数据"""
        p = self._get_market_file()
        if not p.exists():
            return {'listings': [], 'transactions': []}
        return json.loads(p.read_text(encoding='utf-8'))
    
    def _save_market(self, data: Dict):
        """保存市场数据"""
        p = self._get_market_file()
        p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    
    def list_ingredient_for_sale(self, user_id: str, ingredient_id: str, quantity: int, price: int) -> Dict:
        """上架食材出售"""
        rem = check_cooldown(user_id, 'chef', 'market')
        if rem > 0:
            raise RuntimeError(f"cooldown:{rem}")
        
        chef_data = self._load_chef_data(user_id)
        if not chef_data:
            raise ValueError("你还不是厨师！")
        
        user = self.dm.load_user(user_id) or {}
        
        # 检查背包中是否有足够的食材
        backpack = user.get('backpack', [])
        ingredient_item = next((b for b in backpack if b.get('id') == ingredient_id and b.get('type') == 'ingredient'), None)
        
        if not ingredient_item:
            raise ValueError("你没有这种食材！")
        
        if ingredient_item.get('amount', 0) < quantity:
            raise ValueError(f"食材数量不足！你只有{ingredient_item.get('amount', 0)}个")
        
        if price < 1:
            raise ValueError("价格必须大于0！")
        
        # 从背包移除
        ingredient_item['amount'] -= quantity
        if ingredient_item['amount'] <= 0:
            backpack.remove(ingredient_item)
        
        self.dm.save_user(user_id, user)
        
        # 创建挂单
        market = self._load_market()
        listing = {
            'id': f"listing_{int(datetime.now().timestamp() * 1000)}",
            'seller_id': user_id,
            'ingredient_id': ingredient_id,
            'ingredient_name': ingredient_item['name'],
            'quantity': quantity,
            'price_per_unit': price,
            'total_price': price * quantity,
            'created_time': datetime.now().isoformat()
        }
        
        market['listings'].append(listing)
        self._save_market(market)
        
        set_cooldown(user_id, 'chef', 'market', 10)
        
        return {"success": True, "listing": listing}
    
    def cancel_listing(self, user_id: str, listing_id: str) -> Dict:
        """取消挂单"""
        market = self._load_market()
        listing_idx = next((i for i, l in enumerate(market['listings']) if l['id'] == listing_id), None)
        
        if listing_idx is None:
            raise ValueError("挂单不存在！")
        
        listing = market['listings'][listing_idx]
        
        if listing['seller_id'] != user_id:
            raise ValueError("这不是你的挂单！")
        
        # 返还食材
        user = self.dm.load_user(user_id) or {'backpack': []}
        backpack = user.get('backpack', [])
        
        existing = next((b for b in backpack if b.get('id') == listing['ingredient_id'] and b.get('type') == 'ingredient'), None)
        if existing:
            existing['amount'] = existing.get('amount', 0) + listing['quantity']
        else:
            backpack.append({
                'id': listing['ingredient_id'],
                'name': listing['ingredient_name'],
                'type': 'ingredient',
                'amount': listing['quantity']
            })
        
        self.dm.save_user(user_id, user)
        
        # 移除挂单
        market['listings'].pop(listing_idx)
        self._save_market(market)
        
        return {"success": True, "cancelled_listing": listing}
    
    def buy_from_market(self, user_id: str, listing_id: str) -> Dict:
        """从市场购买"""
        rem = check_cooldown(user_id, 'chef', 'buy_market')
        if rem > 0:
            raise RuntimeError(f"cooldown:{rem}")
        
        market = self._load_market()
        listing_idx = next((i for i, l in enumerate(market['listings']) if l['id'] == listing_id), None)
        
        if listing_idx is None:
            raise ValueError("挂单不存在！")
        
        listing = market['listings'][listing_idx]
        
        if listing['seller_id'] == user_id:
            raise ValueError("不能购买自己的挂单！")
        
        # 检查买家资金
        buyer = self.dm.load_user(user_id) or {'money': 0, 'backpack': []}
        total_price = listing['total_price']
        
        if buyer.get('money', 0) < total_price:
            raise ValueError(f"金币不足！需要{total_price}金币")
        
        # 扣钱、给食材
        buyer['money'] -= total_price
        
        backpack = buyer.get('backpack', [])
        existing = next((b for b in backpack if b.get('id') == listing['ingredient_id'] and b.get('type') == 'ingredient'), None)
        if existing:
            existing['amount'] = existing.get('amount', 0) + listing['quantity']
        else:
            backpack.append({
                'id': listing['ingredient_id'],
                'name': listing['ingredient_name'],
                'type': 'ingredient',
                'amount': listing['quantity']
            })
        
        self.dm.save_user(user_id, buyer)
        
        # 给卖家钱
        seller = self.dm.load_user(listing['seller_id']) or {'money': 0}
        seller['money'] = seller.get('money', 0) + total_price
        self.dm.save_user(listing['seller_id'], seller)
        
        # 记录交易
        transaction = {
            'buyer_id': user_id,
            'seller_id': listing['seller_id'],
            'listing': listing,
            'time': datetime.now().isoformat()
        }
        market['transactions'].append(transaction)
        
        # 只保留最近100条交易
        if len(market['transactions']) > 100:
            market['transactions'] = market['transactions'][-100:]
        
        # 移除挂单
        market['listings'].pop(listing_idx)
        self._save_market(market)
        
        set_cooldown(user_id, 'chef', 'buy_market', 5)
        
        return {"success": True, "purchased": listing, "cost": total_price}
    
    def get_market_listings(self) -> List[Dict]:
        """获取市场挂单列表"""
        market = self._load_market()
        return market.get('listings', [])
    
    def get_my_listings(self, user_id: str) -> List[Dict]:
        """获取我的挂单"""
        market = self._load_market()
        return [l for l in market.get('listings', []) if l['seller_id'] == user_id]

    # ========== 高级功能：合作料理系统 ==========
    
    def _get_coop_file(self) -> Path:
        return self.data_root / 'chef_coop.json'
    
    def _load_coop_data(self) -> Dict:
        """加载合作料理数据"""
        p = self._get_coop_file()
        if not p.exists():
            return {'active': [], 'history': []}
        return json.loads(p.read_text(encoding='utf-8'))
    
    def _save_coop_data(self, data: Dict):
        """保存合作料理数据"""
        p = self._get_coop_file()
        p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    
    def create_coop_cooking(self, user_id: str, recipe_id: str, participant_ids: List[str]) -> Dict:
        """发起合作料理"""
        rem = check_cooldown(user_id, 'chef', 'coop')
        if rem > 0:
            raise RuntimeError(f"cooldown:{rem}")
        
        chef_data = self._load_chef_data(user_id)
        if not chef_data:
            raise ValueError("你还不是厨师！")
        
        # 检查食谱
        recipe = next((r for r in self.recipes if r['id'] == recipe_id), None)
        if not recipe:
            raise ValueError("食谱不存在！")
        
        if recipe_id not in chef_data['recipes']:
            raise ValueError("你还没有掌握这个食谱！")
        
        # 检查参与者
        if len(participant_ids) > 3:
            raise ValueError("合作料理最多支持4人（你和3位参与者）！")
        
        for pid in participant_ids:
            p_chef = self._load_chef_data(pid)
            if not p_chef:
                raise ValueError(f"用户 {pid} 还不是厨师！")
        
        # 创建合作料理
        coop = {
            'id': f"coop_{int(datetime.now().timestamp() * 1000)}",
            'recipe_id': recipe_id,
            'recipe_name': recipe['name'],
            'initiator_id': user_id,
            'participants': {
                user_id: {'joined': True, 'contributed': False, 'ingredients': []}
            },
            'quality_bonus': 0,
            'status': 'preparing',
            'created_time': datetime.now().isoformat()
        }
        
        # 添加被邀请的参与者
        for pid in participant_ids:
            coop['participants'][pid] = {'joined': False, 'contributed': False, 'ingredients': []}
        
        coop_data = self._load_coop_data()
        coop_data['active'].append(coop)
        self._save_coop_data(coop_data)
        
        set_cooldown(user_id, 'chef', 'coop', 300)  # 5分钟冷却
        
        return {"success": True, "coop": coop, "recipe": recipe}
    
    def join_coop_cooking(self, user_id: str, coop_id: str) -> Dict:
        """加入合作料理"""
        chef_data = self._load_chef_data(user_id)
        if not chef_data:
            raise ValueError("你还不是厨师！")
        
        coop_data = self._load_coop_data()
        coop = next((c for c in coop_data['active'] if c['id'] == coop_id), None)
        
        if not coop:
            raise ValueError("合作料理不存在或已结束！")
        
        if coop['status'] != 'preparing':
            raise ValueError("该合作料理已经开始或结束！")
        
        if user_id not in coop['participants']:
            raise ValueError("你没有被邀请参与此合作料理！")
        
        if coop['participants'][user_id]['joined']:
            raise ValueError("你已经加入了！")
        
        coop['participants'][user_id]['joined'] = True
        self._save_coop_data(coop_data)
        
        return {"success": True, "coop": coop}
    
    def contribute_to_coop(self, user_id: str, coop_id: str, ingredient_id: str, amount: int = 1) -> Dict:
        """贡献食材到合作料理"""
        rem = check_cooldown(user_id, 'chef', 'contribute')
        if rem > 0:
            raise RuntimeError(f"cooldown:{rem}")
        
        chef_data = self._load_chef_data(user_id)
        if not chef_data:
            raise ValueError("你还不是厨师！")
        
        coop_data = self._load_coop_data()
        coop = next((c for c in coop_data['active'] if c['id'] == coop_id), None)
        
        if not coop:
            raise ValueError("合作料理不存在！")
        
        if user_id not in coop['participants']:
            raise ValueError("你不是此合作料理的参与者！")
        
        if not coop['participants'][user_id]['joined']:
            raise ValueError("请先加入合作料理！")
        
        if coop['status'] != 'preparing':
            raise ValueError("该合作料理已经开始或结束！")
        
        # 检查用户背包
        user = self.dm.load_user(user_id) or {'backpack': []}
        backpack = user.get('backpack', [])
        
        ing_item = next((b for b in backpack if b.get('id') == ingredient_id and b.get('type') == 'ingredient'), None)
        if not ing_item:
            raise ValueError("你没有这种食材！")
        
        if ing_item.get('amount', 0) < amount:
            raise ValueError(f"食材数量不足！只有{ing_item.get('amount', 0)}个")
        
        # 扣除食材
        ing_item['amount'] -= amount
        if ing_item['amount'] <= 0:
            backpack.remove(ing_item)
        self.dm.save_user(user_id, user)
        
        # 添加贡献
        coop['participants'][user_id]['ingredients'].append({
            'id': ingredient_id,
            'name': ing_item['name'],
            'amount': amount
        })
        coop['participants'][user_id]['contributed'] = True
        
        # 计算品质加成（检查是否是食谱所需）
        recipe = next((r for r in self.recipes if r['id'] == coop['recipe_id']), None)
        is_required = False
        if recipe:
            is_required = any(ing['id'] == ingredient_id for ing in recipe.get('ingredients', []))
        
        quality_bonus = (5 if is_required else 2) * amount
        coop['quality_bonus'] += quality_bonus
        
        # 检查是否所有已加入的人都贡献了
        all_contributed = all(
            p['contributed'] for p in coop['participants'].values() if p['joined']
        )
        if all_contributed:
            coop['status'] = 'ready'
        
        self._save_coop_data(coop_data)
        
        set_cooldown(user_id, 'chef', 'contribute', 10)
        
        return {
            "success": True,
            "ingredient": ing_item['name'],
            "amount": amount,
            "quality_bonus": quality_bonus,
            "is_required": is_required,
            "coop_status": coop['status']
        }
    
    def complete_coop_cooking(self, user_id: str, coop_id: str) -> Dict:
        """完成合作料理"""
        coop_data = self._load_coop_data()
        coop_idx = next((i for i, c in enumerate(coop_data['active']) if c['id'] == coop_id), None)
        
        if coop_idx is None:
            raise ValueError("合作料理不存在！")
        
        coop = coop_data['active'][coop_idx]
        
        if coop['initiator_id'] != user_id:
            raise ValueError("只有发起者才能完成合作料理！")
        
        if coop['status'] == 'completed':
            raise ValueError("该合作料理已经完成！")
        
        # 检查是否所有人都贡献了
        joined_count = sum(1 for p in coop['participants'].values() if p['joined'])
        contributed_count = sum(1 for p in coop['participants'].values() if p['contributed'])
        
        if contributed_count < joined_count:
            raise ValueError("还有参与者未贡献食材！")
        
        # 计算成功率
        base_success = 70 + (joined_count * 5) + (coop['quality_bonus'] // 2)
        success_rate = min(95, base_success)
        
        is_success = random.random() * 100 <= success_rate
        
        if not is_success:
            coop['status'] = 'failed'
            coop['completed_time'] = datetime.now().isoformat()
            
            coop_data['active'].pop(coop_idx)
            coop_data['history'].append(coop)
            self._save_coop_data(coop_data)
            
            return {
                "success": False,
                "message": "合作料理失败了！",
                "success_rate": success_rate
            }
        
        # 成功 - 计算品质
        quality = min(100, 50 + coop['quality_bonus'] + (joined_count * 5))
        
        # 创建料理
        recipe = next((r for r in self.recipes if r['id'] == coop['recipe_id']), None)
        dish_id = f"coop_dish_{int(datetime.now().timestamp() * 1000)}"
        
        # 给发起者背包添加料理
        initiator = self.dm.load_user(user_id) or {'backpack': []}
        initiator['backpack'].append({
            'id': dish_id,
            'name': coop['recipe_name'],
            'type': 'dish',
            'quality': quality,
            'base_price': int(recipe['basePrice'] * 1.5) if recipe else 50,
            'coop': True
        })
        self.dm.save_user(user_id, initiator)
        
        # 给所有参与者发放奖励
        rewards = []
        for pid, pdata in coop['participants'].items():
            if pdata['contributed']:
                p_chef = self._load_chef_data(pid)
                if p_chef:
                    exp_gain = 20 + quality // 5
                    rep_gain = quality // 20
                    
                    p_chef['exp'] += exp_gain
                    p_chef['reputation'] += rep_gain
                    
                    # 检查升级
                    while p_chef['exp'] >= p_chef['level'] * 100:
                        p_chef['level'] += 1
                        p_chef['exp'] -= (p_chef['level'] - 1) * 100
                    
                    self._save_chef_data(pid, p_chef)
                    
                    # 检查成就
                    self._check_achievements(pid, p_chef)
                    
                    rewards.append({
                        'user_id': pid,
                        'exp': exp_gain,
                        'reputation': rep_gain
                    })
        
        # 更新状态
        coop['status'] = 'completed'
        coop['completed_time'] = datetime.now().isoformat()
        coop['result_quality'] = quality
        
        coop_data['active'].pop(coop_idx)
        coop_data['history'].append(coop)
        
        # 保留最近20条历史
        if len(coop_data['history']) > 20:
            coop_data['history'] = coop_data['history'][-20:]
        
        self._save_coop_data(coop_data)
        
        return {
            "success": True,
            "quality": quality,
            "dish_name": coop['recipe_name'],
            "rewards": rewards,
            "participant_count": joined_count
        }
    
    def get_coop_cooking(self, coop_id: str) -> Optional[Dict]:
        """获取合作料理详情"""
        coop_data = self._load_coop_data()
        return next((c for c in coop_data['active'] if c['id'] == coop_id), None)
    
    def list_my_coop_cooking(self, user_id: str) -> List[Dict]:
        """列出我参与的合作料理"""
        coop_data = self._load_coop_data()
        return [c for c in coop_data['active'] if user_id in c['participants']]
    
    # ========== 高级功能：成就系统 ==========
    
    def _get_achievements_file(self) -> Path:
        return self.data_root / 'chef_achievements.json'
    
    def _load_achievements_config(self) -> List[Dict]:
        """加载成就配置"""
        # 默认成就配置
        default_achievements = [
            {
                "id": "first_dish",
                "name": "初出茅庐",
                "description": "成功制作第一道料理",
                "category": "cooking",
                "requirement_type": "success_count",
                "requirement_value": 1,
                "reward_exp": 50,
                "reward_reputation": 5,
                "reward_title": "新手厨师"
            },
            {
                "id": "cooking_10",
                "name": "厨艺初成",
                "description": "成功制作10道料理",
                "category": "cooking",
                "requirement_type": "success_count",
                "requirement_value": 10,
                "reward_exp": 100,
                "reward_reputation": 10
            },
            {
                "id": "cooking_50",
                "name": "烹饪能手",
                "description": "成功制作50道料理",
                "category": "cooking",
                "requirement_type": "success_count",
                "requirement_value": 50,
                "reward_money": 500,
                "reward_exp": 200,
                "reward_reputation": 20,
                "reward_title": "烹饪能手"
            },
            {
                "id": "cooking_100",
                "name": "厨艺精通",
                "description": "成功制作100道料理",
                "category": "cooking",
                "requirement_type": "success_count",
                "requirement_value": 100,
                "reward_money": 1000,
                "reward_exp": 500,
                "reward_reputation": 50,
                "reward_title": "料理大师"
            },
            {
                "id": "level_5",
                "name": "厨师进阶",
                "description": "厨师等级达到5级",
                "category": "cooking",
                "requirement_type": "level",
                "requirement_value": 5,
                "reward_money": 300,
                "reward_exp": 150
            },
            {
                "id": "level_10",
                "name": "资深厨师",
                "description": "厨师等级达到10级",
                "category": "cooking",
                "requirement_type": "level",
                "requirement_value": 10,
                "reward_money": 1000,
                "reward_reputation": 30,
                "reward_title": "资深厨师"
            },
            {
                "id": "recipes_5",
                "name": "食谱收藏家",
                "description": "学会5种食谱",
                "category": "collection",
                "requirement_type": "recipes",
                "requirement_value": 5,
                "reward_exp": 100
            },
            {
                "id": "recipes_10",
                "name": "美食百科",
                "description": "学会10种食谱",
                "category": "collection",
                "requirement_type": "recipes",
                "requirement_value": 10,
                "reward_money": 500,
                "reward_reputation": 15,
                "reward_title": "美食家"
            },
            {
                "id": "reputation_100",
                "name": "声名鹊起",
                "description": "声望达到100",
                "category": "social",
                "requirement_type": "reputation",
                "requirement_value": 100,
                "reward_money": 500,
                "reward_exp": 200
            },
            {
                "id": "reputation_500",
                "name": "名厨之路",
                "description": "声望达到500",
                "category": "social",
                "requirement_type": "reputation",
                "requirement_value": 500,
                "reward_money": 2000,
                "reward_title": "知名厨师"
            },
            {
                "id": "team_leader",
                "name": "团队领袖",
                "description": "成功创建一个厨师团队",
                "category": "social",
                "requirement_type": "team_created",
                "requirement_value": 1,
                "reward_exp": 100,
                "reward_reputation": 10
            },
            {
                "id": "contest_winner",
                "name": "比赛冠军",
                "description": "在厨艺比赛中获得第一名",
                "category": "special",
                "requirement_type": "contest_wins",
                "requirement_value": 1,
                "reward_money": 300,
                "reward_reputation": 20,
                "reward_title": "厨艺冠军"
            },
            {
                "id": "coop_master",
                "name": "合作达人",
                "description": "完成5次合作料理",
                "category": "social",
                "requirement_type": "coop_count",
                "requirement_value": 5,
                "reward_exp": 150,
                "reward_reputation": 15
            }
        ]
        return default_achievements
    
    def _get_user_achievements_file(self, user_id: str) -> Path:
        return self.chef_data_dir / f"{user_id}_achievements.json"
    
    def _load_user_achievements(self, user_id: str) -> Dict:
        """加载用户成就数据"""
        p = self._get_user_achievements_file(user_id)
        if not p.exists():
            return {
                'unlocked': [],
                'progress': {},
                'titles': [],
                'current_title': None
            }
        return json.loads(p.read_text(encoding='utf-8'))
    
    def _save_user_achievements(self, user_id: str, data: Dict):
        """保存用户成就数据"""
        p = self._get_user_achievements_file(user_id)
        p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    
    def _check_achievements(self, user_id: str, chef_data: Dict) -> List[Dict]:
        """检查并解锁成就"""
        achievements = self._load_achievements_config()
        user_ach = self._load_user_achievements(user_id)
        
        newly_unlocked = []
        
        for ach in achievements:
            if ach['id'] in user_ach['unlocked']:
                continue  # 已解锁
            
            # 检查是否满足条件
            req_type = ach['requirement_type']
            req_value = ach['requirement_value']
            current_value = 0
            
            if req_type == 'success_count':
                current_value = chef_data.get('success_count', 0)
            elif req_type == 'level':
                current_value = chef_data.get('level', 1)
            elif req_type == 'recipes':
                current_value = len(chef_data.get('recipes', []))
            elif req_type == 'reputation':
                current_value = chef_data.get('reputation', 0)
            elif req_type == 'team_created':
                # 检查是否创建过团队
                teams = self._load_teams()
                current_value = 1 if any(t['leader_id'] == user_id for t in teams) else 0
            elif req_type == 'contest_wins':
                current_value = user_ach.get('progress', {}).get('contest_wins', 0)
            elif req_type == 'coop_count':
                current_value = user_ach.get('progress', {}).get('coop_count', 0)
            
            # 更新进度
            user_ach['progress'][req_type] = current_value
            
            # 检查是否解锁
            if current_value >= req_value:
                user_ach['unlocked'].append(ach['id'])
                
                # 发放奖励
                if ach.get('reward_money'):
                    user = self.dm.load_user(user_id) or {}
                    user['money'] = user.get('money', 0) + ach['reward_money']
                    self.dm.save_user(user_id, user)
                
                if ach.get('reward_exp'):
                    chef_data['exp'] += ach['reward_exp']
                
                if ach.get('reward_reputation'):
                    chef_data['reputation'] += ach['reward_reputation']
                
                if ach.get('reward_title'):
                    if ach['reward_title'] not in user_ach['titles']:
                        user_ach['titles'].append(ach['reward_title'])
                
                newly_unlocked.append(ach)
        
        if newly_unlocked:
            self._save_user_achievements(user_id, user_ach)
            self._save_chef_data(user_id, chef_data)
        
        return newly_unlocked
    
    def check_and_unlock_achievements(self, user_id: str) -> List[Dict]:
        """主动检查成就"""
        chef_data = self._load_chef_data(user_id)
        if not chef_data:
            raise ValueError("你还不是厨师！")
        return self._check_achievements(user_id, chef_data)
    
    def get_all_achievements(self) -> List[Dict]:
        """获取所有成就列表"""
        return self._load_achievements_config()
    
    def get_user_achievements(self, user_id: str) -> Dict:
        """获取用户成就信息"""
        chef_data = self._load_chef_data(user_id)
        if not chef_data:
            raise ValueError("你还不是厨师！")
        
        all_achievements = self._load_achievements_config()
        user_ach = self._load_user_achievements(user_id)
        
        unlocked_list = []
        locked_list = []
        
        for ach in all_achievements:
            ach_copy = ach.copy()
            if ach['id'] in user_ach['unlocked']:
                ach_copy['status'] = 'unlocked'
                unlocked_list.append(ach_copy)
            else:
                ach_copy['status'] = 'locked'
                # 添加当前进度
                req_type = ach['requirement_type']
                ach_copy['current_progress'] = user_ach.get('progress', {}).get(req_type, 0)
                locked_list.append(ach_copy)
        
        return {
            'unlocked': unlocked_list,
            'locked': locked_list,
            'titles': user_ach.get('titles', []),
            'current_title': user_ach.get('current_title'),
            'total_unlocked': len(unlocked_list),
            'total_achievements': len(all_achievements)
        }
    
    def set_title(self, user_id: str, title: str) -> Dict:
        """设置当前称号"""
        user_ach = self._load_user_achievements(user_id)
        
        if title not in user_ach.get('titles', []):
            raise ValueError("你还没有解锁这个称号！")
        
        user_ach['current_title'] = title
        self._save_user_achievements(user_id, user_ach)
        
        return {"success": True, "title": title}
    
    def record_contest_win(self, user_id: str):
        """记录比赛获胜（内部调用）"""
        user_ach = self._load_user_achievements(user_id)
        user_ach['progress']['contest_wins'] = user_ach.get('progress', {}).get('contest_wins', 0) + 1
        self._save_user_achievements(user_id, user_ach)
    
    def record_coop_complete(self, user_id: str):
        """记录合作料理完成（内部调用）"""
        user_ach = self._load_user_achievements(user_id)
        user_ach['progress']['coop_count'] = user_ach.get('progress', {}).get('coop_count', 0) + 1
        self._save_user_achievements(user_id, user_ach)
