from core.fishing.logic import FishingLogic
from core.common.data_manager import DataManager


def test_go_fishing(tmp_path):
    fp = tmp_path / 'data' / 'fishing'
    fp.mkdir(parents=True)
    fish = {'fish':[{'id':'F1','name':'鲤鱼','rarity':1,'price':5},{'id':'F2','name':'金鱼','rarity':8,'price':50}]}
    (fp / 'fish.json').write_text(__import__('json').dumps(fish, ensure_ascii=False))

    dm = DataManager(base_path=tmp_path)
    fl = FishingLogic(data_manager=dm)
    user = 'angler'
    caught = fl.go_fishing(user)
    assert 'name' in caught
    u = dm.load_user(user)
    assert 'inventory' in u and 'fish' in u['inventory']
