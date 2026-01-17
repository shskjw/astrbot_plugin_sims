from core.netbar.logic import NetbarLogic
from core.common.data_manager import DataManager


def test_recharge_and_buy_hours(tmp_path):
    dm = DataManager(base_path=tmp_path)
    nl = NetbarLogic(data_manager=dm)
    user = 'nb1'
    nl.recharge(user, 50)
    u = nl.get_user(user)
    assert u['balance'] == 50
    nl.buy_hour(user, 2, price_per_hour=5)
    u2 = nl.get_user(user)
    assert u2['hours_remaining'] == 2


def test_buy_vip(tmp_path):
    dm = DataManager(base_path=tmp_path)
    nl = NetbarLogic(data_manager=dm)
    user = 'nb2'
    nl.recharge(user, 500)
    nl.buy_vip(user, 3, price_per_month=100)
    u = nl.get_user(user)
    assert u['vip_until'] > 0
