from core.stock.logic import StockMarket
from core.common.data_manager import DataManager
from core.stock.models import StockData


def test_buy_and_sell(tmp_path):
    dm = DataManager(base_path=tmp_path)
    sm = StockMarket()
    sm.register_stock(StockData(id='S1', name='TestCo', price=10.0, volatility=0.3))
    user = 'trader'
    dm.save_user(user, {'name':'trader','money':1000})
    # buy 5
    cur = sm.buy(dm, user, 'S1', 5)
    assert cur['amount'] == 5
    u = dm.load_user(user)
    assert u['money'] == 1000 - 5*10.0
    # sell 2
    res = sm.sell(dm, user, 'S1', 2)
    assert res['remaining'] == 3
    u2 = dm.load_user(user)
    assert u2['money'] > 1000 - 5*10.0


def test_list_holdings(tmp_path):
    dm = DataManager(base_path=tmp_path)
    sm = StockMarket()
    sm.register_stock(StockData(id='S2', name='Other', price=5.0, volatility=0.1))
    user = 't2'
    dm.save_user(user, {'name':'t2','money':100})
    sm.buy(dm, user, 'S2', 2)
    holdings = sm.list_holdings(dm, user)
    assert 'S2' in holdings
