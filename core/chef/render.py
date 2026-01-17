"""Chef subsystem renderer for displaying game information."""

from typing import Dict, List, Any
from ..common.image_utils import HTMLRenderer
from ..common.screenshot import html_to_image_bytes


class ChefRenderer:
    """Renders chef-related information."""
    
    def __init__(self):
        self.renderer = HTMLRenderer()
    
    def render_recipes(self, recipes: List[Dict], known: List[str] = None, level: int = 1) -> str:
        """渲染食谱列表"""
        known = known or []
        lines = ["【食谱列表】\n"]
        
        for recipe in recipes:
            status = "✓已学" if recipe['id'] in known else "✗未学"
            lock_info = f" (需要等级{recipe['unlockLevel']})" if level < recipe['unlockLevel'] else ""
            lines.append(f"[{recipe['id']}] {recipe['name']}{lock_info} - {status}")
            lines.append(f"   难度:{recipe['difficulty']} 经验:{recipe['exp']} 售价:{recipe['basePrice']}")
        
        return "\n".join(lines)
    
    def render_cook_result(self, success: bool, recipe: Dict, chef_level: int, chef_exp: int) -> str:
        """渲染烹饪结果"""
        if success:
            return f"""【料理成功！】
{recipe['name']} 制作成功！
获得经验: {recipe['exp']}
厨师等级: {chef_level} (经验: {chef_exp})
出售价格: {recipe['basePrice']}金币"""
        else:
            return f"""【料理失败】
{recipe['name']} 烹饪失败，重新尝试吧～"""
    
    def render_ingredients(self, ingredients: List[Dict], user_inventory: Dict[str, int] = None) -> str:
        """渲染食材列表"""
        user_inventory = user_inventory or {}
        lines = ["【食材商店】\n"]
        
        for ingredient in ingredients:
            owned = user_inventory.get(ingredient['id'], 0)
            lines.append(f"[{ingredient['id']}] {ingredient['name']}")
            lines.append(f"   稀有度: {ingredient['rarity']} 价格: {ingredient['price']}金币 (已有:{owned})")
        
        return "\n".join(lines)
    
    def render_buy_ingredient(self, ingredient: Dict, amount: int, cost: int) -> str:
        """渲染购买食材结果"""
        return f"""【购买成功】
{ingredient['name']} x{amount}
总花费: {cost}金币"""
    
    def render_kitchenware(self, kitchenware: List[Dict], level: int = 1, owned: List[str] = None) -> str:
        """渲染厨具列表"""
        owned = owned or []
        lines = ["【厨具商店】\n"]
        
        for kw in kitchenware:
            status = "✓已有" if kw['id'] in owned else ""
            lock_info = "" if level >= kw['unlockLevel'] else f" (需要等级{kw['unlockLevel']})"
            lines.append(f"[{kw['id']}] {kw['name']}{status}{lock_info}")
            lines.append(f"   价格: {kw['price']}金币")
            lines.append(f"   效果: 成功率+{kw.get('successRateBonus', 0)}% "
                       f"品质+{kw.get('qualityBonus', 0)} 时间-{kw.get('timeReduction', 0)}秒")
        
        return "\n".join(lines)
    
    def render_buy_kitchenware(self, kitchenware: Dict, cost: int) -> str:
        """渲染购买厨具结果"""
        return f"""【购买成功】
{kitchenware['name']}
花费: {cost}金币
效果: {kitchenware['description']}"""
    
    def render_chef_info(self, chef_data: Dict) -> str:
        """渲染厨师信息"""
        success_rate = (chef_data['success_count'] / chef_data['total_count'] * 100 
                       if chef_data['total_count'] > 0 else 0)
        
        return f"""【厨师信息】
等级: {chef_data['level']}
经验: {chef_data['exp']}
已学食谱: {len(chef_data['recipes'])}个
成功率: {success_rate:.1f}% ({chef_data['success_count']}/{chef_data['total_count']})
声望: {chef_data['reputation']}"""
    
    def render_learn_recipe(self, recipe: Dict, cost: int) -> str:
        """渲染学习食谱"""
        return f"""【学习食谱】
{recipe['name']}
花费: {cost}金币
难度: {recipe['difficulty']}
经验回报: {recipe['exp']}"""
    
    def render_sell_dish(self, dish: Dict, price: int) -> str:
        """渲染出售料理"""
        return f"""【出售成功】
{dish['name']}
获得金币: {price}"""
    
    def render_become_chef(self) -> str:
        """渲染成为厨师"""
        return """【成为厨师】
恭喜你成为一名厨师！
你已解锁初级食谱: 番茄蛋汤
发送 #查看食谱 了解可用食谱
发送 #制作料理 开始烹饪"""
