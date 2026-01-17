"""
高级功能测试用例
测试酒馆和厨师系统的高级功能
"""
import pytest
import tempfile
import shutil
from pathlib import Path
from datetime import datetime


@pytest.fixture
def temp_data_dir():
    """创建临时数据目录"""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def data_manager(temp_data_dir):
    """创建数据管理器"""
    from core.common.data_manager import DataManager
    dm = DataManager(root=temp_data_dir)
    return dm


@pytest.fixture
def tavern_logic(data_manager, temp_data_dir):
    """创建酒馆逻辑实例"""
    from core.tavern.logic import TavernLogic
    logic = TavernLogic(data_manager)
    logic.data_path = Path(temp_data_dir) / 'tavern'
    logic.data_path.mkdir(parents=True, exist_ok=True)
    return logic


@pytest.fixture
def chef_logic(data_manager, temp_data_dir):
    """创建厨师逻辑实例"""
    from core.chef.logic import ChefLogic
    logic = ChefLogic(data_manager)
    logic.data_root = Path(temp_data_dir)
    logic.chef_data_dir = Path(temp_data_dir) / 'chef_users'
    logic.chef_data_dir.mkdir(parents=True, exist_ok=True)
    return logic


@pytest.fixture
def sample_user_id():
    return "test_user_12345"


@pytest.fixture
def setup_tavern(tavern_logic, data_manager, sample_user_id):
    """设置测试酒馆"""
    # 给用户足够的钱
    data_manager.save_user(sample_user_id, {"money": 100000})
    # 创建酒馆
    tavern_logic.create_tavern(sample_user_id, "测试酒馆", 100000)
    return tavern_logic


@pytest.fixture
def setup_chef(chef_logic, data_manager, sample_user_id):
    """设置测试厨师"""
    data_manager.save_user(sample_user_id, {"money": 100000, "backpack": []})
    chef_logic.become_chef(sample_user_id)
    return chef_logic


# ========== 酒馆高级功能测试 ==========

class TestTavernRanking:
    """酒馆排行榜测试"""
    
    def test_get_ranking_empty(self, tavern_logic):
        """测试空排行榜"""
        rankings = tavern_logic.get_tavern_ranking()
        assert isinstance(rankings, list)
    
    def test_get_ranking_with_taverns(self, setup_tavern, sample_user_id):
        """测试有酒馆的排行榜"""
        rankings = setup_tavern.get_tavern_ranking()
        assert len(rankings) >= 1
        assert rankings[0]['user_id'] == sample_user_id
    
    def test_get_my_rank(self, setup_tavern, sample_user_id):
        """测试获取自己的排名"""
        my_rank = setup_tavern.get_my_rank(sample_user_id)
        assert my_rank is not None
        assert my_rank['user_id'] == sample_user_id
        assert my_rank['rank'] >= 1
    
    def test_rank_score_calculation(self, setup_tavern, sample_user_id):
        """测试排名分数计算"""
        my_rank = setup_tavern.get_my_rank(sample_user_id)
        assert 'rank_score' in my_rank
        assert my_rank['rank_score'] > 0


# ========== 合作料理测试 ==========

class TestCoopCooking:
    """合作料理测试"""
    
    def test_create_coop_cooking(self, setup_chef, sample_user_id, chef_logic, data_manager):
        """测试发起合作料理"""
        # 设置另一个厨师
        other_user = "other_chef_123"
        data_manager.save_user(other_user, {"money": 10000, "backpack": []})
        chef_logic.become_chef(other_user)
        
        result = chef_logic.create_coop_cooking(sample_user_id, "soup_01", [other_user])
        assert result['success'] is True
        assert 'coop' in result
        assert result['coop']['recipe_id'] == 'soup_01'
    
    def test_join_coop_cooking(self, setup_chef, sample_user_id, chef_logic, data_manager):
        """测试加入合作料理"""
        other_user = "other_chef_456"
        data_manager.save_user(other_user, {"money": 10000, "backpack": []})
        chef_logic.become_chef(other_user)
        
        # 发起合作
        create_res = chef_logic.create_coop_cooking(sample_user_id, "soup_01", [other_user])
        coop_id = create_res['coop']['id']
        
        # 加入合作
        join_res = chef_logic.join_coop_cooking(other_user, coop_id)
        assert join_res['success'] is True
    
    def test_list_my_coop(self, setup_chef, sample_user_id, chef_logic):
        """测试列出我的合作料理"""
        coops = chef_logic.list_my_coop_cooking(sample_user_id)
        assert isinstance(coops, list)


# ========== 厨师成就测试 ==========

class TestChefAchievements:
    """厨师成就测试"""
    
    def test_get_all_achievements(self, chef_logic):
        """测试获取所有成就"""
        achievements = chef_logic.get_all_achievements()
        assert isinstance(achievements, list)
        assert len(achievements) > 0
    
    def test_get_user_achievements(self, setup_chef, sample_user_id, chef_logic):
        """测试获取用户成就"""
        result = chef_logic.get_user_achievements(sample_user_id)
        assert 'unlocked' in result
        assert 'locked' in result
        assert 'titles' in result
        assert result['total_achievements'] > 0
    
    def test_check_achievements(self, setup_chef, sample_user_id, chef_logic):
        """测试检查成就"""
        # 模拟制作一道料理增加成功次数
        chef_data = chef_logic._load_chef_data(sample_user_id)
        chef_data['success_count'] = 1
        chef_logic._save_chef_data(sample_user_id, chef_data)
        
        newly_unlocked = chef_logic.check_and_unlock_achievements(sample_user_id)
        # 可能解锁"初出茅庐"成就
        assert isinstance(newly_unlocked, list)
    
    def test_set_title(self, setup_chef, sample_user_id, chef_logic):
        """测试设置称号"""
        # 先解锁一个称号
        user_ach = chef_logic._load_user_achievements(sample_user_id)
        user_ach['titles'].append("测试称号")
        chef_logic._save_user_achievements(sample_user_id, user_ach)
        
        result = chef_logic.set_title(sample_user_id, "测试称号")
        assert result['success'] is True
        assert result['title'] == "测试称号"


# ========== 酒馆特殊活动测试 ==========

class TestTavernActivities:
    """酒馆特殊活动测试"""
    
    def test_list_available_activities(self, setup_tavern, sample_user_id):
        """测试列出可用活动"""
        activities = setup_tavern.list_available_activities(sample_user_id)
        assert isinstance(activities, list)
        assert len(activities) > 0
    
    def test_host_activity(self, setup_tavern, sample_user_id, data_manager):
        """测试举办活动"""
        data_manager.save_user(sample_user_id, {"money": 100000})
        
        result = setup_tavern.host_activity(sample_user_id, "happy_hour")
        assert result['success'] is True
        assert 'activity' in result
        assert result['cost'] == 200
    
    def test_list_active_activities(self, setup_tavern):
        """测试列出进行中的活动"""
        activities = setup_tavern.list_active_activities()
        assert isinstance(activities, list)


# ========== 合作酿酒测试 ==========

class TestBrewingProjects:
    """合作酿酒测试"""
    
    def test_list_brewing_recipes(self, tavern_logic):
        """测试列出酿酒配方"""
        recipes = tavern_logic.list_brewing_recipes()
        assert isinstance(recipes, list)
        assert len(recipes) > 0
    
    def test_start_brewing(self, setup_tavern, sample_user_id, data_manager):
        """测试发起酿酒"""
        data_manager.save_user(sample_user_id, {"money": 100000})
        
        result = setup_tavern.start_brewing(sample_user_id, "craft_beer", "我的精酿")
        assert result['success'] is True
        assert result['project']['name'] == "我的精酿"
    
    def test_list_brewing_projects(self, setup_tavern):
        """测试列出酿酒项目"""
        projects = setup_tavern.list_brewing_projects()
        assert isinstance(projects, list)
    
    def test_join_brewing(self, setup_tavern, sample_user_id, data_manager, tavern_logic):
        """测试参与酿酒"""
        # 创建另一个酒馆主
        other_user = "other_tavern_789"
        data_manager.save_user(other_user, {"money": 100000})
        tavern_logic.create_tavern(other_user, "其他酒馆", 100000)
        
        # 发起酿酒
        data_manager.save_user(sample_user_id, {"money": 100000})
        start_res = setup_tavern.start_brewing(sample_user_id, "craft_beer", "合作啤酒")
        project_id = start_res['project']['id']
        
        # 参与酿酒
        join_res = tavern_logic.join_brewing(other_user, project_id, 200)
        assert join_res['success'] is True
        assert join_res['contribution'] == 200


class TestTavernVisit:
    """酒馆参观测试"""
    
    def test_visit_tavern_success(self, setup_tavern, data_manager, sample_user_id):
        """测试参观酒馆成功"""
        # 创建另一个用户的酒馆
        other_user = "other_user_67890"
        data_manager.save_user(other_user, {"money": 100000})
        setup_tavern.create_tavern(other_user, "另一家酒馆", 100000)
        
        # 参观
        result = setup_tavern.visit_tavern(sample_user_id, other_user)
        assert result['success']
        assert 'target_tavern' in result
        assert result['target_tavern']['name'] == "另一家酒馆"
    
    def test_visit_own_tavern_fails(self, setup_tavern, sample_user_id):
        """测试不能参观自己的酒馆"""
        with pytest.raises(ValueError, match="不能参观自己"):
            setup_tavern.visit_tavern(sample_user_id, sample_user_id)
    
    def test_visit_nonexistent_tavern(self, setup_tavern, sample_user_id):
        """测试参观不存在的酒馆"""
        with pytest.raises(ValueError, match="没有酒馆"):
            setup_tavern.visit_tavern(sample_user_id, "nonexistent_user")


class TestTavernRating:
    """酒馆评分测试"""
    
    def test_rate_tavern_success(self, setup_tavern, data_manager, sample_user_id):
        """测试评分成功"""
        # 创建另一个用户的酒馆
        other_user = "other_user_rating"
        data_manager.save_user(other_user, {"money": 100000})
        setup_tavern.create_tavern(other_user, "评分测试酒馆", 100000)
        
        # 评分
        result = setup_tavern.rate_tavern(sample_user_id, other_user, 5, "很棒！")
        assert result['success']
        assert result['rating'] == 5
        assert result['new_average'] == 5.0
    
    def test_rate_invalid_score(self, setup_tavern, data_manager, sample_user_id):
        """测试无效评分"""
        other_user = "other_user_invalid"
        data_manager.save_user(other_user, {"money": 100000})
        setup_tavern.create_tavern(other_user, "无效评分测试", 100000)
        
        with pytest.raises(ValueError, match="1-5"):
            setup_tavern.rate_tavern(sample_user_id, other_user, 10)
    
    def test_get_tavern_ratings(self, setup_tavern, sample_user_id):
        """测试获取酒馆评分"""
        ratings = setup_tavern.get_tavern_ratings(sample_user_id)
        assert 'tavern_name' in ratings
        assert 'average' in ratings
        assert 'total_ratings' in ratings


class TestTavernEvents:
    """酒馆事件测试"""
    
    def test_trigger_random_event(self, setup_tavern, sample_user_id):
        """测试触发随机事件"""
        # 多次尝试触发事件
        event = None
        for _ in range(20):
            event = setup_tavern.trigger_random_event(sample_user_id)
            if event:
                break
        # 不一定每次都触发，所以不断言必须有事件
        if event:
            assert 'id' in event
            assert 'title' in event
    
    def test_get_event_history(self, setup_tavern, sample_user_id):
        """测试获取事件历史"""
        history = setup_tavern.get_event_history(sample_user_id)
        assert isinstance(history, list)


# ========== 厨师高级功能测试 ==========

class TestChefTeam:
    """厨师团队测试"""
    
    def test_create_team_success(self, setup_chef, data_manager, sample_user_id):
        """测试创建团队成功"""
        # 提升等级到3级
        chef_data = setup_chef._load_chef_data(sample_user_id)
        chef_data['level'] = 3
        setup_chef._save_chef_data(sample_user_id, chef_data)
        
        result = setup_chef.create_team(sample_user_id, "测试团队")
        assert result['success']
        assert result['team']['name'] == "测试团队"
        assert sample_user_id in result['team']['members']
    
    def test_create_team_level_requirement(self, setup_chef, sample_user_id):
        """测试等级要求"""
        with pytest.raises(ValueError, match="等级"):
            setup_chef.create_team(sample_user_id, "低等级团队")
    
    def test_get_user_team(self, setup_chef, data_manager, sample_user_id):
        """测试获取用户团队"""
        # 先创建团队
        chef_data = setup_chef._load_chef_data(sample_user_id)
        chef_data['level'] = 3
        setup_chef._save_chef_data(sample_user_id, chef_data)
        setup_chef.create_team(sample_user_id, "查询测试团队")
        
        team = setup_chef.get_user_team(sample_user_id)
        assert team is not None
        assert team['name'] == "查询测试团队"
    
    def test_team_ranking(self, setup_chef, sample_user_id):
        """测试团队排行榜"""
        rankings = setup_chef.get_team_ranking()
        assert isinstance(rankings, list)


class TestChefContest:
    """厨艺比赛测试"""
    
    def test_create_contest_success(self, setup_chef, data_manager, sample_user_id):
        """测试创建比赛成功"""
        # 提升等级
        chef_data = setup_chef._load_chef_data(sample_user_id)
        chef_data['level'] = 3
        chef_data['recipes'] = ['soup_01']
        setup_chef._save_chef_data(sample_user_id, chef_data)
        
        # 添加一个测试食谱
        setup_chef.recipes = [{'id': 'soup_01', 'name': '番茄蛋汤'}]
        
        result = setup_chef.create_contest(sample_user_id, "测试比赛", "soup_01")
        assert result['success']
        assert result['contest']['name'] == "测试比赛"
        assert result['contest']['status'] == 'active'
    
    def test_list_active_contests(self, setup_chef):
        """测试列出活跃比赛"""
        contests = setup_chef.list_active_contests()
        assert isinstance(contests, list)
    
    def test_join_and_submit(self, setup_chef, data_manager, sample_user_id):
        """测试参加和提交比赛"""
        # 设置
        chef_data = setup_chef._load_chef_data(sample_user_id)
        chef_data['level'] = 3
        chef_data['recipes'] = ['soup_01']
        setup_chef._save_chef_data(sample_user_id, chef_data)
        setup_chef.recipes = [{'id': 'soup_01', 'name': '番茄蛋汤'}]
        
        # 创建比赛
        result = setup_chef.create_contest(sample_user_id, "参与测试", "soup_01")
        contest_id = result['contest']['id']
        
        # 创建另一个用户参加
        other_user = "other_chef_user"
        data_manager.save_user(other_user, {"money": 10000, "backpack": []})
        setup_chef.become_chef(other_user)
        other_chef = setup_chef._load_chef_data(other_user)
        other_chef['recipes'] = ['soup_01']
        setup_chef._save_chef_data(other_user, other_chef)
        
        # 参加比赛
        join_result = setup_chef.join_contest(other_user, contest_id)
        assert join_result['success']
        
        # 提交作品
        submit_result = setup_chef.submit_contest_dish(other_user, contest_id)
        assert submit_result['success']
        assert 'score' in submit_result


class TestChefMarket:
    """食材市场测试"""
    
    def test_list_for_sale(self, setup_chef, data_manager, sample_user_id):
        """测试上架食材"""
        # 给用户添加食材
        user = data_manager.load_user(sample_user_id)
        user['backpack'] = [{
            'id': 'tomato',
            'name': '番茄',
            'type': 'ingredient',
            'amount': 10
        }]
        data_manager.save_user(sample_user_id, user)
        
        result = setup_chef.list_ingredient_for_sale(sample_user_id, 'tomato', 5, 10)
        assert result['success']
        assert result['listing']['quantity'] == 5
        assert result['listing']['price_per_unit'] == 10
    
    def test_cancel_listing(self, setup_chef, data_manager, sample_user_id):
        """测试取消挂单"""
        # 先上架
        user = data_manager.load_user(sample_user_id)
        user['backpack'] = [{
            'id': 'egg',
            'name': '鸡蛋',
            'type': 'ingredient',
            'amount': 20
        }]
        data_manager.save_user(sample_user_id, user)
        
        list_result = setup_chef.list_ingredient_for_sale(sample_user_id, 'egg', 10, 5)
        listing_id = list_result['listing']['id']
        
        # 取消
        cancel_result = setup_chef.cancel_listing(sample_user_id, listing_id)
        assert cancel_result['success']
        
        # 检查食材返还
        user = data_manager.load_user(sample_user_id)
        egg_item = next((b for b in user['backpack'] if b['id'] == 'egg'), None)
        assert egg_item is not None
        assert egg_item['amount'] == 20  # 原来的10 + 返还的10
    
    def test_buy_from_market(self, setup_chef, data_manager, sample_user_id):
        """测试从市场购买"""
        # 卖家上架
        seller_id = "seller_user"
        data_manager.save_user(seller_id, {"money": 1000, "backpack": [{
            'id': 'flour',
            'name': '面粉',
            'type': 'ingredient',
            'amount': 50
        }]})
        setup_chef.become_chef(seller_id)
        list_result = setup_chef.list_ingredient_for_sale(seller_id, 'flour', 20, 5)
        listing_id = list_result['listing']['id']
        
        # 买家购买
        buy_result = setup_chef.buy_from_market(sample_user_id, listing_id)
        assert buy_result['success']
        assert buy_result['cost'] == 100  # 20 * 5
        
        # 检查卖家收到钱
        seller = data_manager.load_user(seller_id)
        assert seller['money'] == 1100  # 1000 + 100
    
    def test_get_market_listings(self, setup_chef):
        """测试获取市场列表"""
        listings = setup_chef.get_market_listings()
        assert isinstance(listings, list)
    
    def test_get_my_listings(self, setup_chef, sample_user_id):
        """测试获取我的挂单"""
        listings = setup_chef.get_my_listings(sample_user_id)
        assert isinstance(listings, list)


# ========== 数据模型测试 ==========

class TestTavernModels:
    """酒馆数据模型测试"""
    
    def test_event_choice_model(self):
        """测试事件选择模型"""
        from core.tavern.models import EventChoice
        choice = EventChoice(
            text="选择A",
            effects={"popularity": 10, "reputation": 5}
        )
        assert choice.text == "选择A"
        assert choice.effects['popularity'] == 10
    
    def test_tavern_rank_entry(self):
        """测试排行榜条目模型"""
        from core.tavern.models import TavernRankEntry
        entry = TavernRankEntry(
            user_id="test",
            tavern_name="测试酒馆",
            level=5,
            total_income=10000,
            reputation=8,
            staff_count=3,
            rank_score=15000
        )
        assert entry.level == 5
        assert entry.rank_score == 15000


class TestChefModels:
    """厨师数据模型测试"""
    
    def test_team_model(self):
        """测试团队模型"""
        from core.chef.models import Team
        team = Team(
            id="team_001",
            name="测试团队",
            leader_id="leader",
            members=["leader", "member1"],
            created_time=datetime.now().isoformat()
        )
        assert team.name == "测试团队"
        assert len(team.members) == 2
    
    def test_contest_model(self):
        """测试比赛模型"""
        from core.chef.models import Contest
        contest = Contest(
            id="contest_001",
            name="测试比赛",
            creator_id="creator",
            participants={},
            status="active",
            created_time=datetime.now().isoformat()
        )
        assert contest.status == "active"
    
    def test_market_listing_model(self):
        """测试市场挂单模型"""
        from core.chef.models import MarketListing
        listing = MarketListing(
            id="listing_001",
            seller_id="seller",
            ingredient_id="tomato",
            ingredient_name="番茄",
            quantity=10,
            price_per_unit=5,
            created_time=datetime.now().isoformat()
        )
        assert listing.quantity == 10
        assert listing.price_per_unit == 5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
