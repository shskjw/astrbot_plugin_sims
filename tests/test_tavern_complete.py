"""
酒馆系统完整测试套件
测试覆盖：创建酒馆、购买物资、菜单管理、营业、升级、员工管理等
"""

import pytest
import json
import tempfile
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

from astrbot_plugin_sims.core.common.data_manager import DataManager
from astrbot_plugin_sims.core.tavern import logic, models


@pytest.fixture
def temp_data_dir():
    """创建临时数据目录"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def data_manager(temp_data_dir):
    """创建数据管理器"""
    dm = DataManager()
    dm.root = temp_data_dir
    return dm


@pytest.fixture
def tavern_logic(data_manager):
    """创建酒馆逻辑实例"""
    return logic.TavernLogic(data_manager)


@pytest.fixture
def tavern_renderer():
    """创建酒馆渲染器"""
    return models.TavernData.model_json_schema  # Just for type checking


@pytest.fixture
def sample_user_id():
    """样本用户ID"""
    return "test_user_123"


@pytest.fixture
def setup_tavern_data(temp_data_dir):
    """设置样本酒馆数据"""
    tavern_dir = Path(temp_data_dir) / 'data' / 'tavern'
    tavern_dir.mkdir(parents=True, exist_ok=True)
    
    # 创建样本饮品数据
    drinks_file = tavern_dir.parent / 'tavern_drinks.json'
    drinks_data = {
        "defaultDrinks": [
            {
                "id": "draft_beer",
                "name": "普通生啤",
                "type": "beer",
                "basePrice": 15,
                "description": "新鲜的生啤酒",
                "ingredients": ["beer_basic"],
                "popularity": 80,
                "alcoholContent": "4.5%",
                "preparationTime": "短",
                "specialEffects": [],
                "sales": 0
            },
            {
                "id": "craft_beer",
                "name": "精酿啤酒",
                "type": "beer",
                "basePrice": 28,
                "description": "特色啤酒",
                "ingredients": ["beer_craft"],
                "popularity": 70,
                "alcoholContent": "5.8%",
                "preparationTime": "中",
                "specialEffects": ["提升心情"],
                "sales": 0
            }
        ]
    }
    drinks_file.write_text(json.dumps(drinks_data), encoding='utf-8')
    
    # 创建样本市场数据
    market_file = tavern_dir.parent / 'tavern_market.json'
    market_data = {
        "lastUpdated": "2023-12-15T00:00:00Z",
        "marketItems": [
            {
                "id": "beer_basic",
                "name": "基础啤酒原料",
                "type": "beer",
                "description": "啤酒基础原料",
                "price": 150,
                "quantity": 30,
                "quality": 1
            },
            {
                "id": "beer_craft",
                "name": "精酿啤酒原料",
                "type": "beer",
                "description": "高质量原料",
                "price": 300,
                "quantity": 20,
                "quality": 2
            }
        ]
    }
    market_file.write_text(json.dumps(market_data), encoding='utf-8')
    
    return tavern_dir


# ========== 基础功能测试 ==========

def test_create_tavern(tavern_logic, data_manager, sample_user_id, setup_tavern_data):
    """测试：创建酒馆"""
    # 设置用户初始资金
    user = {"user_id": sample_user_id, "money": 10000}
    data_manager.save_user(sample_user_id, user)
    
    # 创建酒馆
    result = tavern_logic.create_tavern(sample_user_id, "金色酒馆", 10000)
    
    assert result['success'] == True
    assert result['tavern'].name == "金色酒馆"
    assert result['tavern'].level == 1
    assert result['cost'] == 5000
    
    # 验证用户金币已扣除
    updated_user = data_manager.load_user(sample_user_id)
    assert updated_user['money'] == 5000


def test_create_tavern_duplicate(tavern_logic, data_manager, sample_user_id, setup_tavern_data):
    """测试：不能重复创建酒馆"""
    user = {"user_id": sample_user_id, "money": 10000}
    data_manager.save_user(sample_user_id, user)
    
    # 第一次创建
    tavern_logic.create_tavern(sample_user_id, "第一个酒馆", 10000)
    
    # 第二次创建应该失败
    with pytest.raises(ValueError, match="已经拥有一家酒馆"):
        tavern_logic.create_tavern(sample_user_id, "第二个酒馆", 5000)


def test_create_tavern_insufficient_funds(tavern_logic, sample_user_id, setup_tavern_data):
    """测试：资金不足无法创建酒馆"""
    with pytest.raises(ValueError, match="资金不足"):
        tavern_logic.create_tavern(sample_user_id, "酒馆", 1000)


# ========== 菜单管理测试 ==========

def test_add_custom_menu(tavern_logic, data_manager, sample_user_id, setup_tavern_data):
    """测试：添加自定义菜单"""
    # 先创建酒馆
    user = {"user_id": sample_user_id, "money": 10000}
    data_manager.save_user(sample_user_id, user)
    tavern_logic.create_tavern(sample_user_id, "酒馆", 10000)
    
    # 添加菜单项
    result = tavern_logic.add_custom_menu_item(sample_user_id, "draft_beer", 20)
    
    assert result['success'] == True
    assert result['menu_item']['name'] == "普通生啤"
    assert result['menu_item']['price'] == 20
    
    # 验证菜单已保存
    tavern = tavern_logic._load_tavern_data(sample_user_id)
    assert len(tavern.custom_menu) == 1


def test_add_menu_exceeds_capacity(tavern_logic, data_manager, sample_user_id, setup_tavern_data):
    """测试：菜单容量限制"""
    user = {"user_id": sample_user_id, "money": 50000}
    data_manager.save_user(sample_user_id, user)
    tavern_logic.create_tavern(sample_user_id, "酒馆", 50000)
    
    # 添加10个菜单项（初始等级容量）
    for i in range(10):
        tavern_logic.add_custom_menu_item(sample_user_id, "draft_beer" if i % 2 == 0 else "craft_beer", 20 + i)
    
    # 第11个应该超过容量
    with pytest.raises(ValueError, match="菜单已满"):
        tavern_logic.add_custom_menu_item(sample_user_id, "draft_beer", 25)


# ========== 物资购买测试 ==========

def test_buy_supplies(tavern_logic, data_manager, sample_user_id, setup_tavern_data):
    """测试：购买酒馆物资"""
    user = {"user_id": sample_user_id, "money": 10000}
    data_manager.save_user(sample_user_id, user)
    tavern_logic.create_tavern(sample_user_id, "酒馆", 10000)
    
    # 购买物资
    result = tavern_logic.buy_supplies(sample_user_id, "beer_basic", 5, 5000)
    
    assert result['success'] == True
    assert result['quantity'] == 5
    assert result['total_price'] == 750  # 150 * 5
    
    # 验证库存已增加
    tavern = tavern_logic._load_tavern_data(sample_user_id)
    assert tavern.supplies.beer_basic == 25  # 20初始 + 5购买


def test_buy_supplies_insufficient_funds(tavern_logic, data_manager, sample_user_id, setup_tavern_data):
    """测试：资金不足无法购买"""
    user = {"user_id": sample_user_id, "money": 100}
    data_manager.save_user(sample_user_id, user)
    tavern_logic.create_tavern(sample_user_id, "酒馆", 100)
    
    with pytest.raises(ValueError, match="资金不足"):
        tavern_logic.buy_supplies(sample_user_id, "beer_basic", 10, 100)


# ========== 营业系统测试 ==========

def test_operate_tavern(tavern_logic, data_manager, sample_user_id, setup_tavern_data):
    """测试：营业酒馆获取收入"""
    user = {"user_id": sample_user_id, "money": 10000}
    data_manager.save_user(sample_user_id, user)
    tavern_logic.create_tavern(sample_user_id, "酒馆", 10000)
    
    # 添加菜单项
    tavern_logic.add_custom_menu_item(sample_user_id, "draft_beer", 20)
    
    # 营业
    result = tavern_logic.operate_tavern(sample_user_id)
    
    assert result['success'] == True
    assert result['customers'] > 0
    assert result['profit'] > 0
    assert result['tavern'].daily_income > 0


def test_operate_tavern_empty_menu(tavern_logic, data_manager, sample_user_id, setup_tavern_data):
    """测试：菜单为空无法营业"""
    user = {"user_id": sample_user_id, "money": 10000}
    data_manager.save_user(sample_user_id, user)
    tavern_logic.create_tavern(sample_user_id, "酒馆", 10000)
    
    with pytest.raises(ValueError, match="菜单是空的"):
        tavern_logic.operate_tavern(sample_user_id)


def test_operate_tavern_insufficient_supplies(tavern_logic, data_manager, sample_user_id, setup_tavern_data):
    """测试：物资不足无法营业"""
    user = {"user_id": sample_user_id, "money": 10000}
    data_manager.save_user(sample_user_id, user)
    tavern_logic.create_tavern(sample_user_id, "酒馆", 10000)
    tavern_logic.add_custom_menu_item(sample_user_id, "draft_beer", 20)
    
    # 清空物资
    tavern = tavern_logic._load_tavern_data(sample_user_id)
    tavern.supplies = models.TavernSupplies()
    tavern_logic._save_tavern_data(sample_user_id, tavern)
    
    with pytest.raises(ValueError, match="缺少必要的物资"):
        tavern_logic.operate_tavern(sample_user_id)


# ========== 升级系统测试 ==========

def test_upgrade_tavern(tavern_logic, data_manager, sample_user_id, setup_tavern_data):
    """测试：升级酒馆"""
    user = {"user_id": sample_user_id, "money": 50000}
    data_manager.save_user(sample_user_id, user)
    tavern_logic.create_tavern(sample_user_id, "酒馆", 50000)
    
    prev_capacity = 20
    result = tavern_logic.upgrade_tavern(sample_user_id, 45000)
    
    assert result['success'] == True
    assert result['tavern'].level == 2
    assert result['tavern'].capacity == 30
    assert result['upgrade_cost'] == 5000


def test_upgrade_tavern_max_level(tavern_logic, data_manager, sample_user_id, setup_tavern_data):
    """测试：最高等级无法升级"""
    user = {"user_id": sample_user_id, "money": 50000}
    data_manager.save_user(sample_user_id, user)
    tavern_logic.create_tavern(sample_user_id, "酒馆", 50000)
    
    # 手动设置为最高等级
    tavern = tavern_logic._load_tavern_data(sample_user_id)
    tavern.level = 10
    tavern_logic._save_tavern_data(sample_user_id, tavern)
    
    with pytest.raises(ValueError, match="已经达到最高等级"):
        tavern_logic.upgrade_tavern(sample_user_id, 50000)


# ========== 员工管理测试 ==========

def test_hire_staff(tavern_logic, data_manager, sample_user_id, setup_tavern_data):
    """测试：雇佣员工"""
    user = {"user_id": sample_user_id, "money": 50000}
    data_manager.save_user(sample_user_id, user)
    tavern_logic.create_tavern(sample_user_id, "酒馆", 50000)
    
    result = tavern_logic.hire_staff(sample_user_id, "bartender", 45000)
    
    assert result['success'] == True
    assert result['staff'].staff_type == "bartender"
    assert result['hire_cost'] == 500  # 100 * 5
    
    # 验证员工已保存
    tavern = tavern_logic._load_tavern_data(sample_user_id)
    assert len(tavern.staff) == 1


def test_hire_staff_duplicate_type(tavern_logic, data_manager, sample_user_id, setup_tavern_data):
    """测试：同类型员工只能雇佣一名"""
    user = {"user_id": sample_user_id, "money": 50000}
    data_manager.save_user(sample_user_id, user)
    tavern_logic.create_tavern(sample_user_id, "酒馆", 50000)
    
    tavern_logic.hire_staff(sample_user_id, "bartender", 50000)
    
    with pytest.raises(ValueError, match="已经雇佣了"):
        tavern_logic.hire_staff(sample_user_id, "bartender", 49500)


def test_hire_staff_level_requirement(tavern_logic, data_manager, sample_user_id, setup_tavern_data):
    """测试：员工等级需求"""
    user = {"user_id": sample_user_id, "money": 50000}
    data_manager.save_user(sample_user_id, user)
    tavern_logic.create_tavern(sample_user_id, "酒馆", 50000)
    
    # 酒馆等级1，无法雇佣需要等级3的保安
    with pytest.raises(ValueError, match="需要酒馆等级达到3级"):
        tavern_logic.hire_staff(sample_user_id, "security", 50000)


def test_fire_staff(tavern_logic, data_manager, sample_user_id, setup_tavern_data):
    """测试：解雇员工"""
    user = {"user_id": sample_user_id, "money": 50000}
    data_manager.save_user(sample_user_id, user)
    tavern_logic.create_tavern(sample_user_id, "酒馆", 50000)
    
    # 雇佣员工
    hire_result = tavern_logic.hire_staff(sample_user_id, "bartender", 50000)
    staff_id = hire_result['staff'].id
    
    # 解雇员工
    fire_result = tavern_logic.fire_staff(sample_user_id, staff_id)
    
    assert fire_result['success'] == True
    
    # 验证员工已移除
    tavern = tavern_logic._load_tavern_data(sample_user_id)
    assert len(tavern.staff) == 0


# ========== 数据模型测试 ==========

def test_tavern_data_model():
    """测试：酒馆数据模型"""
    tavern = models.TavernData(
        user_id="test",
        name="测试酒馆",
        created_at=datetime.now().isoformat()
    )
    
    assert tavern.name == "测试酒馆"
    assert tavern.level == 1
    assert tavern.capacity == 20
    assert len(tavern.staff) == 0


def test_drink_model():
    """测试：饮品数据模型"""
    drink = models.Drink(
        id="test_drink",
        name="测试饮品",
        type="beer",
        base_price=20,
        description="测试",
        ingredients=["beer_basic"],
        alcohol_content="5%",
        preparation_time="短"
    )
    
    assert drink.name == "测试饮品"
    assert drink.base_price == 20


def test_staff_model():
    """测试：员工数据模型"""
    staff = models.Staff(
        id="staff_001",
        name="张三",
        staff_type="bartender",
        salary=100,
        hired_at=datetime.now().isoformat()
    )
    
    assert staff.name == "张三"
    assert staff.salary == 100


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
