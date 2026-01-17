from pathlib import Path
import time
import json
import random
import uuid
from typing import Optional, List, Dict, Any
from datetime import datetime

from ..common.data_manager import DataManager
from ..common.cooldown import check_cooldown, set_cooldown
from .models import (
    NetbarInfo, ComputerConfig, NetbarEmployee, NetbarFacilities,
    NetbarEnvironment, NetbarMaintenance, NetbarStatistics, NetbarMembers,
    NetbarUser, NetbarRankingEntry,
    STAFF_TYPES, COMPUTER_TYPES, FACILITY_TYPES
)


class NetbarLogic:
    def __init__(self, data_manager: Optional[DataManager] = None):
        self.dm = data_manager or DataManager()
        self.data_path = Path(self.dm.root) / 'data' / 'netbar'
        self.data_path.mkdir(parents=True, exist_ok=True)

    # ========== 文件操作 ==========
    def _netbars_file(self) -> Path:
        return self.data_path / 'netbars.json'

    def _users_file(self) -> Path:
        return self.data_path / 'users.json'

    def _load_netbars(self) -> dict:
        p = self._netbars_file()
        if not p.exists():
            return {}
        return json.loads(p.read_text(encoding='utf-8'))

    def _save_netbars(self, data: dict):
        p = self._netbars_file()
        p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')

    def _load_users(self) -> dict:
        p = self._users_file()
        if not p.exists():
            return {}
        return json.loads(p.read_text(encoding='utf-8'))

    def _save_users(self, data: dict):
        p = self._users_file()
        p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')

    # ========== 网吧数据操作 ==========
    def _get_user_netbar(self, user_id: str) -> Optional[NetbarInfo]:
        """获取用户的网吧"""
        netbars = self._load_netbars()
        if user_id in netbars:
            return NetbarInfo(**netbars[user_id])
        return None

    def _save_user_netbar(self, user_id: str, netbar: NetbarInfo):
        """保存用户的网吧"""
        netbars = self._load_netbars()
        netbars[user_id] = netbar.dict()
        self._save_netbars(netbars)

    def _update_netbar_status(self, netbar: NetbarInfo) -> NetbarInfo:
        """更新网吧状态（收入、维护等）"""
        last_update = datetime.fromisoformat(netbar.last_update)
        now = datetime.now()
        hours_passed = (now - last_update).total_seconds() / 3600
        
        if hours_passed < 1:
            return netbar
        
        hours = int(hours_passed)
        
        # 计算每小时收入
        computers = netbar.computers
        hourly_income = (
            computers.basic * 5 * netbar.statistics.basic_usage +
            computers.standard * 8 * netbar.statistics.standard_usage +
            computers.premium * 15 * netbar.statistics.premium_usage
        )
        
        # 设施收入
        if netbar.facilities.snack_bar:
            hourly_income += 20
        
        # 员工工资（按小时计算）
        hourly_expense = sum(e.salary / 720 for e in netbar.staff)  # 月薪/720小时
        
        # 更新收入
        income = int(hourly_income * hours)
        expense = int(hourly_expense * hours)
        netbar.income += income
        netbar.expenses += expense
        netbar.daily_income = income
        netbar.daily_expenses = expense
        
        # 维护状态下降
        maintenance_decay = hours * 0.5
        netbar.maintenance.status = max(0, netbar.maintenance.status - maintenance_decay)
        
        # 清洁度下降
        cleanliness_decay = hours * 0.3
        has_cleaner = any(e.position == "保洁" for e in netbar.staff)
        if has_cleaner:
            cleanliness_decay *= 0.3
        netbar.cleanliness = max(0, netbar.cleanliness - cleanliness_decay)
        
        # 更新客户数量
        base_customers = (computers.basic + computers.standard + computers.premium) * 0.3
        reputation_mult = netbar.reputation / 100
        netbar.statistics.current_customers = int(base_customers * reputation_mult)
        netbar.statistics.total_customers += netbar.statistics.current_customers * hours
        
        # 更新时间
        netbar.last_update = now.isoformat()
        
        return netbar

    # ========== 核心功能 ==========
    def create_netbar(self, user_id: str, name: str = None) -> NetbarInfo:
        """创建网吧"""
        rem = check_cooldown(user_id, 'netbar', 'create')
        if rem > 0:
            raise RuntimeError(f"cooldown:{rem}")
        
        existing = self._get_user_netbar(user_id)
        if existing:
            raise ValueError("你已经拥有一家网吧了！")
        
        # 检查资金
        user = self.dm.load_user(user_id) or {}
        if user.get('money', 0) < 50000:
            raise ValueError("创建网吧需要50000元启动资金！")
        
        # 扣除资金
        user['money'] -= 50000
        user['happiness'] = user.get('happiness', 50) + 10
        self.dm.save_user(user_id, user)
        
        # 创建网吧
        netbar_id = str(uuid.uuid4())[:8]
        user_name = user.get('name', f'用户{user_id[:6]}')
        netbar_name = name or f"{user_name}的网吧"
        
        netbar = NetbarInfo(
            id=netbar_id,
            owner_id=user_id,
            name=netbar_name
        )
        
        self._save_user_netbar(user_id, netbar)
        
        set_cooldown(user_id, 'netbar', 'create', 60)
        
        return netbar

    def get_netbar_info(self, user_id: str) -> NetbarInfo:
        """获取网吧信息"""
        rem = check_cooldown(user_id, 'netbar', 'info')
        if rem > 0:
            raise RuntimeError(f"cooldown:{rem}")
        
        netbar = self._get_user_netbar(user_id)
        if not netbar:
            raise ValueError("你还没有网吧！请使用【创建网吧】指令创建一家网吧。")
        
        # 更新状态
        netbar = self._update_netbar_status(netbar)
        self._save_user_netbar(user_id, netbar)
        
        set_cooldown(user_id, 'netbar', 'info', 3)
        
        return netbar

    def hire_employee(self, user_id: str, position: str) -> dict:
        """雇佣员工"""
        rem = check_cooldown(user_id, 'netbar', 'hire')
        if rem > 0:
            raise RuntimeError(f"cooldown:{rem}")
        
        netbar = self._get_user_netbar(user_id)
        if not netbar:
            raise ValueError("你还没有网吧！")
        
        if position not in STAFF_TYPES:
            available = '、'.join(STAFF_TYPES.keys())
            raise ValueError(f"无效的职位！可选职位：{available}")
        
        staff_config = STAFF_TYPES[position]
        
        # 检查员工上限
        staff_limit = netbar.level * 3
        if len(netbar.staff) >= staff_limit:
            raise ValueError(f"当前网吧等级最多雇佣{staff_limit}名员工！请先升级网吧。")
        
        # 检查资金
        user = self.dm.load_user(user_id) or {}
        salary = staff_config['salary']
        if user.get('money', 0) < salary:
            raise ValueError(f"雇佣{position}需要{salary}元，资金不足！")
        
        # 扣费并雇佣
        user['money'] -= salary
        
        employee_id = f"EMP{uuid.uuid4().hex[:6].upper()}"
        employee = NetbarEmployee(
            id=employee_id,
            position=position,
            salary=salary,
            skill=staff_config['skill']
        )
        netbar.staff.append(employee)
        netbar.expenses += salary
        netbar.reputation += 5
        
        # 保洁特殊效果
        if position == "保洁":
            netbar.cleanliness = min(100, netbar.cleanliness + 20)
        
        self.dm.save_user(user_id, user)
        self._save_user_netbar(user_id, netbar)
        
        set_cooldown(user_id, 'netbar', 'hire', 30)
        
        return {
            "employee_id": employee_id,
            "position": position,
            "salary": salary,
            "skill": staff_config['skill'],
            "description": staff_config['description']
        }

    def fire_employee(self, user_id: str, employee_id: str) -> dict:
        """解雇员工"""
        rem = check_cooldown(user_id, 'netbar', 'fire')
        if rem > 0:
            raise RuntimeError(f"cooldown:{rem}")
        
        netbar = self._get_user_netbar(user_id)
        if not netbar:
            raise ValueError("你还没有网吧！")
        
        # 查找员工
        employee_idx = None
        employee = None
        for i, e in enumerate(netbar.staff):
            if e.id == employee_id:
                employee_idx = i
                employee = e
                break
        
        if employee is None:
            staff_list = ', '.join(f"{e.position}({e.id})" for e in netbar.staff) or "无"
            raise ValueError(f"未找到该员工！当前员工：{staff_list}")
        
        # 计算遣散费
        hire_date = datetime.fromisoformat(employee.hire_date)
        work_days = max(1, (datetime.now() - hire_date).days)
        severance_pay = int(employee.salary * (work_days / 30) * 0.5)
        
        user = self.dm.load_user(user_id) or {}
        if user.get('money', 0) < severance_pay:
            raise ValueError(f"解雇员工需要支付{severance_pay}元遣散费，资金不足！")
        
        # 执行解雇
        user['money'] -= severance_pay
        netbar.staff.pop(employee_idx)
        netbar.expenses += severance_pay
        netbar.reputation = max(0, netbar.reputation - 5)
        
        # 保洁特殊效果
        if employee.position == "保洁":
            netbar.cleanliness = max(0, netbar.cleanliness - 20)
        
        self.dm.save_user(user_id, user)
        self._save_user_netbar(user_id, netbar)
        
        set_cooldown(user_id, 'netbar', 'fire', 30)
        
        return {
            "position": employee.position,
            "work_days": work_days,
            "severance_pay": severance_pay
        }

    def buy_equipment(self, user_id: str, eq_type: str, count: int) -> dict:
        """购买设备"""
        rem = check_cooldown(user_id, 'netbar', 'buy_equipment')
        if rem > 0:
            raise RuntimeError(f"cooldown:{rem}")
        
        netbar = self._get_user_netbar(user_id)
        if not netbar:
            raise ValueError("你还没有网吧！")
        
        if eq_type not in COMPUTER_TYPES:
            available = '、'.join(COMPUTER_TYPES.keys())
            raise ValueError(f"无效的设备类型！可选：{available}")
        
        if count <= 0:
            raise ValueError("购买数量必须大于0！")
        
        config = COMPUTER_TYPES[eq_type]
        
        # 检查空间限制
        computers = netbar.computers
        current_total = computers.basic + computers.standard + computers.premium
        space_limit = netbar.level * 10
        
        if current_total + count > space_limit:
            raise ValueError(f"当前网吧等级最多容纳{space_limit}台电脑！请先升级网吧。")
        
        # 检查资金
        total_cost = config['price'] * count
        user = self.dm.load_user(user_id) or {}
        if user.get('money', 0) < total_cost:
            raise ValueError(f"购买{count}台{eq_type}配置电脑需要{total_cost}元，资金不足！")
        
        # 购买
        user['money'] -= total_cost
        key = config['key']
        if key == 'basic':
            netbar.computers.basic += count
        elif key == 'standard':
            netbar.computers.standard += count
        elif key == 'premium':
            netbar.computers.premium += count
        
        netbar.expenses += total_cost
        reputation_gain = count * config['performance'] // 10
        netbar.reputation = min(100, netbar.reputation + reputation_gain)
        
        # 更新使用率
        total_after = current_total + count
        if total_after > 0:
            netbar.statistics.basic_usage = netbar.computers.basic / total_after * 0.6
            netbar.statistics.standard_usage = netbar.computers.standard / total_after * 0.7
            netbar.statistics.premium_usage = netbar.computers.premium / total_after * 0.8
        
        self.dm.save_user(user_id, user)
        self._save_user_netbar(user_id, netbar)
        
        set_cooldown(user_id, 'netbar', 'buy_equipment', 30)
        
        return {
            "type": eq_type,
            "count": count,
            "total_cost": total_cost,
            "reputation_gain": reputation_gain,
            "description": config['description']
        }

    def maintain_equipment(self, user_id: str) -> dict:
        """维护设备"""
        rem = check_cooldown(user_id, 'netbar', 'maintain')
        if rem > 0:
            raise RuntimeError(f"cooldown:{rem}")
        
        netbar = self._get_user_netbar(user_id)
        if not netbar:
            raise ValueError("你还没有网吧！")
        
        # 计算维护费用
        computers = netbar.computers
        basic_cost = computers.basic * COMPUTER_TYPES['基础']['maintenance_cost']
        standard_cost = computers.standard * COMPUTER_TYPES['标准']['maintenance_cost']
        premium_cost = computers.premium * COMPUTER_TYPES['高端']['maintenance_cost']
        total_cost = basic_cost + standard_cost + premium_cost
        
        if total_cost == 0:
            raise ValueError("没有需要维护的设备！")
        
        user = self.dm.load_user(user_id) or {}
        if user.get('money', 0) < total_cost:
            raise ValueError(f"维护设备需要{total_cost}元，资金不足！\n基础:{basic_cost}元 标准:{standard_cost}元 高端:{premium_cost}元")
        
        # 执行维护
        user['money'] -= total_cost
        netbar.maintenance.status = 100
        netbar.maintenance.last_maintenance = datetime.now().isoformat()
        netbar.maintenance.total_cost += total_cost
        netbar.expenses += total_cost
        
        self.dm.save_user(user_id, user)
        self._save_user_netbar(user_id, netbar)
        
        set_cooldown(user_id, 'netbar', 'maintain', 60)
        
        return {
            "basic_cost": basic_cost,
            "standard_cost": standard_cost,
            "premium_cost": premium_cost,
            "total_cost": total_cost
        }

    def upgrade_netbar(self, user_id: str) -> dict:
        """升级网吧"""
        rem = check_cooldown(user_id, 'netbar', 'upgrade')
        if rem > 0:
            raise RuntimeError(f"cooldown:{rem}")
        
        netbar = self._get_user_netbar(user_id)
        if not netbar:
            raise ValueError("你还没有网吧！")
        
        if netbar.level >= 10:
            raise ValueError("网吧已达最高等级！")
        
        # 计算升级费用
        upgrade_cost = netbar.level * 20000
        
        # 检查条件
        if netbar.reputation < netbar.level * 10:
            raise ValueError(f"声誉不足！需要 {netbar.level * 10} 声誉才能升级。")
        
        user = self.dm.load_user(user_id) or {}
        if user.get('money', 0) < upgrade_cost:
            raise ValueError(f"升级网吧需要{upgrade_cost}元，资金不足！")
        
        # 执行升级
        user['money'] -= upgrade_cost
        old_level = netbar.level
        netbar.level += 1
        netbar.expenses += upgrade_cost
        
        # 升级奖励
        netbar.reputation = min(100, netbar.reputation + 10)
        
        self.dm.save_user(user_id, user)
        self._save_user_netbar(user_id, netbar)
        
        set_cooldown(user_id, 'netbar', 'upgrade', 300)
        
        new_staff_limit = netbar.level * 3
        new_computer_limit = netbar.level * 10
        
        return {
            "old_level": old_level,
            "new_level": netbar.level,
            "cost": upgrade_cost,
            "staff_limit": new_staff_limit,
            "computer_limit": new_computer_limit
        }

    def buy_facility(self, user_id: str, facility_name: str) -> dict:
        """购买设施"""
        rem = check_cooldown(user_id, 'netbar', 'buy_facility')
        if rem > 0:
            raise RuntimeError(f"cooldown:{rem}")
        
        netbar = self._get_user_netbar(user_id)
        if not netbar:
            raise ValueError("你还没有网吧！")
        
        if facility_name not in FACILITY_TYPES:
            available = '、'.join(FACILITY_TYPES.keys())
            raise ValueError(f"无效的设施！可选：{available}")
        
        config = FACILITY_TYPES[facility_name]
        key = config['key']
        
        # 检查是否已拥有
        if getattr(netbar.facilities, key, False):
            raise ValueError(f"你已经拥有{facility_name}了！")
        
        price = config['price']
        user = self.dm.load_user(user_id) or {}
        if user.get('money', 0) < price:
            raise ValueError(f"购买{facility_name}需要{price}元，资金不足！")
        
        # 购买
        user['money'] -= price
        setattr(netbar.facilities, key, True)
        netbar.expenses += price
        
        # 设施效果
        if 'reputation_bonus' in config:
            netbar.reputation = min(100, netbar.reputation + config['reputation_bonus'])
        
        self.dm.save_user(user_id, user)
        self._save_user_netbar(user_id, netbar)
        
        set_cooldown(user_id, 'netbar', 'buy_facility', 60)
        
        return {
            "facility_name": facility_name,
            "price": price,
            "description": config['description']
        }

    def collect_income(self, user_id: str) -> dict:
        """收取收入"""
        rem = check_cooldown(user_id, 'netbar', 'collect')
        if rem > 0:
            raise RuntimeError(f"cooldown:{rem}")
        
        netbar = self._get_user_netbar(user_id)
        if not netbar:
            raise ValueError("你还没有网吧！")
        
        # 更新状态
        netbar = self._update_netbar_status(netbar)
        
        # 计算可收取的净收入
        net_income = netbar.income - netbar.expenses
        if net_income <= 0:
            raise ValueError(f"当前没有可收取的收入！收入:{netbar.income} 支出:{netbar.expenses}")
        
        # 收取
        user = self.dm.load_user(user_id) or {}
        user['money'] = user.get('money', 0) + net_income
        
        collected = net_income
        netbar.income = 0
        netbar.expenses = 0
        
        self.dm.save_user(user_id, user)
        self._save_user_netbar(user_id, netbar)
        
        set_cooldown(user_id, 'netbar', 'collect', 60)
        
        return {
            "collected": collected
        }

    def get_netbar_ranking(self, sort_by: str = "reputation") -> List[NetbarRankingEntry]:
        """获取网吧排行榜"""
        netbars = self._load_netbars()
        
        entries = []
        for uid, data in netbars.items():
            user = self.dm.load_user(uid) or {}
            computers = data.get('computers', {})
            total_computers = (
                computers.get('basic', 0) +
                computers.get('standard', 0) +
                computers.get('premium', 0)
            )
            entries.append(NetbarRankingEntry(
                owner_id=uid,
                owner_name=user.get('name', f'用户{uid[:6]}'),
                netbar_name=data.get('name', '网吧'),
                level=data.get('level', 1),
                reputation=data.get('reputation', 50),
                total_income=data.get('income', 0),
                computer_count=total_computers
            ))
        
        # 排序
        if sort_by == "level":
            entries.sort(key=lambda x: x.level, reverse=True)
        elif sort_by == "income":
            entries.sort(key=lambda x: x.total_income, reverse=True)
        elif sort_by == "computers":
            entries.sort(key=lambda x: x.computer_count, reverse=True)
        else:
            entries.sort(key=lambda x: x.reputation, reverse=True)
        
        return entries[:20]

    def get_staff_types(self) -> List[dict]:
        """获取员工类型"""
        return [
            {
                "position": pos,
                "salary": config['salary'],
                "skill": config['skill'],
                "description": config['description']
            }
            for pos, config in STAFF_TYPES.items()
        ]

    def get_equipment_types(self) -> List[dict]:
        """获取设备类型"""
        return [
            {
                "type": name,
                "price": config['price'],
                "performance": config['performance'],
                "maintenance_cost": config['maintenance_cost'],
                "description": config['description']
            }
            for name, config in COMPUTER_TYPES.items()
        ]

    def get_facility_types(self) -> List[dict]:
        """获取设施类型"""
        return [
            {
                "name": name,
                "price": config['price'],
                "description": config['description']
            }
            for name, config in FACILITY_TYPES.items()
        ]

    # ========== 兼容旧接口 ==========
    def get_user(self, user_id: str) -> dict:
        users = self._load_users()
        return users.get(user_id, {'user_id': user_id, 'balance': 0, 'vip_until': 0, 'rented_until': 0, 'hours_remaining': 0})

    def save_user(self, user_id: str, data: dict):
        users = self._load_users()
        users[user_id] = data
        self._save_users(users)

    def recharge(self, user_id: str, amount: int):
        if amount <= 0:
            raise ValueError('充值金额必须大于0')
        user = self.get_user(user_id)
        user['balance'] = user.get('balance', 0) + amount
        self.save_user(user_id, user)
        return user

    def buy_hour(self, user_id: str, hours: int, price_per_hour: int = 1):
        rem = check_cooldown(user_id, 'netbar', 'buy')
        if rem > 0:
            raise RuntimeError(f"cooldown:{rem}")
        if hours <= 0:
            raise ValueError('小时数必须大于0')
        user = self.get_user(user_id)
        cost = hours * price_per_hour
        if user.get('balance', 0) < cost:
            raise ValueError('余额不足')
        user['balance'] -= cost
        user['hours_remaining'] = user.get('hours_remaining', 0) + hours
        user['rented_until'] = int(time.time()) + user['hours_remaining'] * 3600
        self.save_user(user_id, user)
        set_cooldown(user_id, 'netbar', 'buy', 2)
        return user

    def buy_vip(self, user_id: str, months: int, price_per_month: int = 100):
        if months <= 0:
            raise ValueError('月份必须大于0')
        user = self.get_user(user_id)
        cost = months * price_per_month
        if user.get('balance', 0) < cost:
            raise ValueError('余额不足')
        user['balance'] -= cost
        now = int(time.time())
        user['vip_until'] = max(user.get('vip_until', 0), now) + months * 30 * 24 * 3600
        self.save_user(user_id, user)
        return user

    def info(self, user_id: str) -> dict:
        return self.get_user(user_id)