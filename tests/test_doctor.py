from core.doctor.logic import DoctorLogic
from core.common.data_manager import DataManager


def test_register_and_treat(tmp_path):
    dm = DataManager(base_path=tmp_path)
    dl = DoctorLogic(data_manager=dm)
    user_id = 'doc1'
    # register
    d = dl.register_doctor(user_id, {})
    assert d['user_id'] == user_id
    # create a patient and treat
    p = dl.create_patient('小明', '头痛', severity=1)
    res = dl.treat_patient(user_id, p['id'])
    assert res['reward'] >= 1
    u = dm.load_user(user_id)
    assert u.get('money', 0) >= res['reward']
