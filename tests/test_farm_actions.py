from core.farm.logic import FarmLogic
from core.common.data_manager import DataManager
from pathlib import Path
import json


def test_plant_and_harvest(tmp_path):
    # prepare seed data
    farm_dir = tmp_path / 'data' / 'farm'
    farm_dir.mkdir(parents=True)
    seeds = {'seeds':[{'name':'corn','growthDays':0,'yield':3,'price':10}]}
    (farm_dir / 'seeds.json').write_text(json.dumps(seeds, ensure_ascii=False))

    dm = DataManager(base_path=tmp_path)
    farm_logic = FarmLogic(data_manager=dm)
    user_id = 'user1'
    user = {'name':'tester','money':1000}
    # create farm
    f = farm_logic.create_farm(user_id, user)
    # give seed in inventory
    f['inventory']['seeds'].append({'name':'corn','count':2})
    farm_logic.save_farm(user_id, f)
    # plant at plot 0
    farm_logic.plant_seed(user_id, 0, 'corn')
    # update farms (growthDays=0 so should be ready)
    farm_logic.update_farms()
    f2 = farm_logic.load_farm(user_id)
    assert f2['land']['plots'][0]['harvestReady'] is True
    # harvest
    farm_logic.harvest_crop(user_id, 0)
    f3 = farm_logic.load_farm(user_id)
    crops = f3['inventory']['crops']
    assert any(c['name']=='corn' and c['count']>=3 for c in crops)


def test_shop_buy_seed(tmp_path):
    farm_dir = tmp_path / 'data' / 'farm'
    farm_dir.mkdir(parents=True)
    seeds = {'seeds':[{'name':'wheat','growthDays':1,'yield':1,'price':5}]}
    (farm_dir / 'seeds.json').write_text(json.dumps(seeds, ensure_ascii=False))

    dm = DataManager(base_path=tmp_path)
    farm_logic = FarmLogic(data_manager=dm)
    user_id = 'u2'
    user = {'name':'buyer','money':50}
    farm_logic.create_farm(user_id, user)
    farm_logic.buy_seed(user_id, 'wheat', 3)
    f = farm_logic.load_farm(user_id)
    inv_seeds = f['inventory']['seeds']
    assert any(s['name']=='wheat' and s['count']==3 for s in inv_seeds)
    user_after = dm.load_user(user_id)
    assert user_after['money'] == 50 - 3*5
