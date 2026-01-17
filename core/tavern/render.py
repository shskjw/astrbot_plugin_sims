from typing import Dict, List, Optional
from datetime import datetime
from . import models

class TavernRenderer:
    """酒馆系统文本渲染器"""

    def render_tavern_info(self, tavern: models.TavernData, user_money: int) -> str:
        """渲染酒馆信息"""
        return f"""【{tavern.name}酒馆信息】
        
📊 基本信息：
  等级：{tavern.level}级
  人气：{tavern.popularity}点
  容量：{tavern.capacity}人
  
🌟 运营指标：
  清洁度：{tavern.cleanliness}/100
  氛围：{tavern.atmosphere}/100
  声誉：{tavern.reputation}/10
  顾客满意度：{tavern.customer_satisfaction}%
  
💰 财务信息：
  每日收入：{tavern.daily_income}元
  总收入：{tavern.total_income}元
  你的资金：{user_money}元
  
👥 员工数量：{len(tavern.staff)}/{min(5, tavern.level)}人
🍹 菜单项目：{len(tavern.custom_menu)}个
"""

    def render_market(self, items: List[models.MarketItem]) -> str:
        """渲染酒馆市场"""
        text = "【酒馆市场物资列表】\n\n"
        for item in items:
            quality_star = "⭐" * item.quality
            text += f"  {item.id}: {item.name} {quality_star}\n"
            text += f"     价格：{item.price}元/份 | 库存：{item.quantity}份\n"
            text += f"     类型：{item.type} | {item.description}\n\n"
        text += "\n💡 购买格式：#购买酒馆物资 <物资ID> [数量]\n"
        return text

    def render_operate_result(self, result: Dict) -> str:
        """渲染营业结果"""
        return f"""【今日营业成果】

📊 营业数据：
  客流量：{result['customers']}人
  人均消费：{result['avg_consumption']}元
  总营收：{result['income']}元
  
💼 支出情况：
  员工工资：{result['staff_salary']}元
  净利润：{result['profit']}元 ✨
  
📈 酒馆状态：
  总累计收入：{result['tavern'].total_income}元
  人气：{result['tavern'].popularity}点
  清洁度：{result['tavern'].cleanliness}/100
"""

    def render_upgrade_result(self, result: Dict) -> str:
        """渲染升级结果"""
        return f"""【酒馆升级完成】

🎉 升级成功！

📊 升级收益：
  等级：{result['tavern'].level - 1}级 → {result['tavern'].level}级
  容量提升：{result['prev_capacity']}人 → {result['tavern'].capacity}人 (+{result['capacity_increase']}人)
  氛围提升：+5点
  声誉提升：+1点
  菜单容量：+2个位置
  
💰 升级费用：{result['upgrade_cost']}元
"""

    def render_create_tavern(self, tavern: models.TavernData, cost: int) -> str:
        """渲染创建酒馆"""
        return f"""【酒馆创建成功】

🎉 欢迎成为酒馆老板！

🏠 酒馆信息：
  名称：{tavern.name}
  等级：{tavern.level}级
  容量：{tavern.capacity}人
  
💰 创建费用：{cost}元

📌 下一步建议：
  1. 使用 #酒馆市场 购买酒馆物资
  2. 使用 #添加菜单 添加特色饮品
  3. 使用 #营业酒馆 开始赚钱
"""

    def render_staff_list(self, staff: List[models.Staff]) -> str:
        """渲染员工列表"""
        if not staff:
            return "【酒馆员工】\n\n你还没有雇佣任何员工。\n\n可用员工类型：\n  - bartender（酒保）\n  - waiter（服务员）\n  - cleaner（清洁工）\n  - security（保安）\n  - musician（驻唱歌手）\n"
        
        text = "【酒馆员工】\n\n"
        for s in staff:
            text += f"  {s.name} - {s.staff_type}\n"
            text += f"     等级：{s.level} | 薪资：{s.salary}元/天\n\n"
        
        text += f"共 {len(staff)} 名员工\n"
        return text
