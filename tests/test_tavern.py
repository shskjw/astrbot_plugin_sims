from core.tavern.logic import TavernLogic
from core.common.data_manager import DataManager


def test_order_drink(tmp_path):
    tp = tmp_path / 'data' / 'tavern'
    tp.mkdir(parents=True)
    drinks = {'drinks':[{'id':'D1','name':'啤酒','price':5,'effect':'放松'}]}
    (tp / 'drinks.json').write_text(__import__('json').dumps(drinks, ensure_ascii=False))

    dm = DataManager(base_path=tmp_path)
    tl = TavernLogic(data_manager=dm)
    user = 'drinker'
    dm.save_user(user, {'money':100})
    d = tl.order_drink(user, '啤酒')
    assert d['price'] == 5
    u = dm.load_user(user)
    assert u['money'] == 95
