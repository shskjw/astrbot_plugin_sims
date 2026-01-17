from core.police.logic import PoliceLogic
from core.common.data_manager import DataManager


def test_create_and_accept_case(tmp_path):
    dm = DataManager(base_path=tmp_path)
    p = PoliceLogic(data_manager=dm)
    case = p.create_case('失窃案','某处失窃，请调查', reward=50)
    assert case['id']
    user_id = 'u_police'
    # accept
    c = p.accept_case(user_id, case['id'])
    assert c['accepted_by']==user_id
    # complete
    p.complete_case(user_id, case['id'])
    user = dm.load_user(user_id)
    assert user.get('money',0) >= 50
