from core.chef.logic import ChefLogic
from core.common.data_manager import DataManager


def test_cook(tmp_path):
    cp = tmp_path / 'data' / 'chef'
    cp.mkdir(parents=True)
    recipes = {'recipes':[{'id':'R1','name':'番茄鸡蛋','ingredients':['番茄','鸡蛋'],'cooking_time':10,'reward':20}]}
    (cp / 'recipes.json').write_text(__import__('json').dumps(recipes, ensure_ascii=False))

    dm = DataManager(base_path=tmp_path)
    cl = ChefLogic(data_manager=dm)
    user = 'chef1'
    dm.save_user(user, {'money':0})
    res = cl.cook(user, '番茄鸡蛋')
    assert res['reward'] == 20
    u = dm.load_user(user)
    assert u['money'] >= 20
