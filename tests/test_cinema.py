from core.cinema.logic import CinemaLogic
from core.common.data_manager import DataManager


def test_watch_movie(tmp_path):
    cp = tmp_path / 'data' / 'cinema'
    cp.mkdir(parents=True)
    movies = {'movies':[{'id':'M1','title':'英雄','price':10,'duration':120}]}
    (cp / 'movies.json').write_text(__import__('json').dumps(movies, ensure_ascii=False))

    dm = DataManager(base_path=tmp_path)
    cl = CinemaLogic(data_manager=dm)
    user = 'moviefan'
    dm.save_user(user, {'money':100})
    m = cl.watch_movie(user, 'M1')
    assert m['price'] == 10
    u = dm.load_user(user)
    assert u['money'] == 90


def test_create_theater(tmp_path):
    dm = DataManager(base_path=tmp_path)
    cl = CinemaLogic(data_manager=dm)
    user = 'owner'
    dm.save_user(user, {'money':2000})
    t = cl.create_theater(user, '宏伟电影院')
    assert t['name'] == '宏伟电影院'
    u = dm.load_user(user)
    assert u['money'] == 1000
