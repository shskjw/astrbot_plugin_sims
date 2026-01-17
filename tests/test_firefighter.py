from core.firefighter.logic import FirefighterLogic
from core.common.data_manager import DataManager


def test_create_accept_complete(tmp_path):
    dm = DataManager(base_path=tmp_path)
    fl = FirefighterLogic(data_manager=dm)
    m = fl.create_mission('火灾', difficulty=2, reward=30)
    assert m['id']
    user = 'ff1'
    fl.accept_mission(user, m['id'])
    res = fl.complete_mission(user, m['id'])
    assert res['reward'] == 30
    u = dm.load_user(user)
    assert u.get('money',0) >= 30
