from core.farm.logic import FarmLogic
from core.common.data_manager import DataManager


def test_create_and_view(tmp_path):
    dm = DataManager(base_path=tmp_path)
    farm = FarmLogic(data_manager=dm)
    user_id = 'u1'
    user = {'name': '测试', 'money': 1000}
    f = farm.create_farm(user_id, user)
    assert f['name'].startswith('测试')
    loaded = farm.load_farm(user_id)
    assert loaded is not None
    # buy land
    user['money'] = 2000
    res = farm.buy_land(user_id, user)
    assert res['land']['level'] >= 1
