from pathlib import Path
import uuid
import random
from typing import Optional, List, Dict, Any
from datetime import datetime
from ..common.data_manager import DataManager
from ..common.cooldown import check_cooldown, set_cooldown
from .models import DoctorInfo, Patient, DoctorSkills, DoctorStats, HospitalInfo, DOCTOR_RANKS

class DoctorLogic:
    def __init__(self, data_manager: Optional[DataManager] = None):
        self.dm = data_manager or DataManager()
        self.data_path = Path(self.dm.root) / 'data' / 'doctor'
        self.data_path.mkdir(parents=True, exist_ok=True)

    def _doctors_file(self):
        return self.data_path / 'doctors.json'

    def _patients_file(self):
        return self.data_path / 'patients.json'

    def _load(self, path):
        if not path.exists():
            return {}
        import json
        return json.loads(path.read_text(encoding='utf-8'))

    def _save(self, path, data):
        import json
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')

    def _load_diseases(self) -> List[dict]:
        """加载疾病数据"""
        p = self.data_path / 'diseases.json'
        if not p.exists():
            return []
        import json
        return json.loads(p.read_text(encoding='utf-8'))

    def _load_medicines(self) -> List[dict]:
        """加载药品数据"""
        p = self.data_path / 'medicines.json'
        if not p.exists():
            return []
        import json
        return json.loads(p.read_text(encoding='utf-8'))

    def _load_surgeries(self) -> List[dict]:
        """加载手术数据"""
        p = self.data_path / 'surgeries.json'
        if not p.exists():
            return []
        import json
        return json.loads(p.read_text(encoding='utf-8'))

    # ========== 基础功能 ==========

    def register_doctor(self, user_id: str, user_info: dict) -> dict:
        """注册成为医生"""
        doctors = self._load(self._doctors_file())
        if user_id in doctors and doctors[user_id].get('rank'):
            raise ValueError('你已经是医生了')
        
        # 初始化医生数据
        d = DoctorInfo(
            user_id=user_id,
            name=user_info.get('name', '医生')
        ).dict()
        
        doctors[user_id] = d
        self._save(self._doctors_file(), doctors)
        
        # persist a flag in user record
        user = self.dm.load_user(user_id) or {}
        user['doctor_registered'] = True
        user['job'] = '医生'
        self.dm.save_user(user_id, user)
        return d

    def get_info(self, user_id: str) -> dict:
        doctors = self._load(self._doctors_file())
        return doctors.get(user_id, {})

    def list_patients(self):
        return list(self._load(self._patients_file()).values())

    def create_patient(self, name: str = None, disease: str = None, severity: int = None):
        """创建患者（可自动生成）"""
        pid = str(uuid.uuid4())[:8]
        
        # 自动生成
        names = ["张三", "李四", "王五", "赵六", "钱七", "孙八", "周九", "吴十"]
        ages = [5, 12, 18, 24, 32, 45, 56, 67, 78]
        genders = ["男", "女"]
        conditions = ["轻症", "重症", "危重"]
        
        diseases = self._load_diseases()
        if diseases:
            random_disease = random.choice(diseases)
            disease_name = random_disease.get('name', '普通感冒')
            disease_id = random_disease.get('id')
            severity = random_disease.get('severity', 3)
            symptoms = random_disease.get('symptoms', [])
        else:
            disease_name = disease or "普通感冒"
            disease_id = None
            severity = severity or random.randint(1, 5)
            symptoms = ["发热", "咳嗽"]
        
        condition = conditions[0] if severity <= 3 else (conditions[1] if severity <= 6 else conditions[2])
        
        p = Patient(
            id=pid,
            name=name or random.choice(names),
            age=random.choice(ages),
            gender=random.choice(genders),
            disease=disease_name,
            disease_id=disease_id,
            severity=severity,
            condition=condition,
            symptoms=symptoms,
            admitted_at=datetime.utcnow().isoformat()
        )
        
        patients = self._load(self._patients_file())
        patients[pid] = p.dict()
        self._save(self._patients_file(), patients)
        return p.dict()

    def treat_patient(self, user_id: str, patient_id: str) -> dict:
        """治疗患者（简单版）"""
        rem = check_cooldown(user_id, 'doctor', 'treat')
        if rem > 0:
            raise RuntimeError(f"cooldown:{rem}")
        
        patients = self._load(self._patients_file())
        p = patients.get(patient_id)
        if not p:
            raise ValueError('患者不存在')
        
        doctors = self._load(self._doctors_file())
        d = doctors.get(user_id)
        if not d:
            raise ValueError('你还不是医生')
        
        severity = p.get('severity', 1)
        reward = max(100, severity * 50)
        exp_gain = severity * 10
        
        # 更新用户金币
        user = self.dm.load_user(user_id) or {}
        user['money'] = user.get('money', 0) + reward
        self.dm.save_user(user_id, user)
        
        # 更新医生数据
        d['experience'] = d.get('experience', 0) + exp_gain
        d['patients_seen'] = d.get('patients_seen', 0) + 1
        if 'stats' not in d:
            d['stats'] = {}
        d['stats']['patients_treated'] = d['stats'].get('patients_treated', 0) + 1
        
        # 检查升级
        self._check_level_up(d)
        
        doctors[user_id] = d
        self._save(self._doctors_file(), doctors)
        
        # 移除患者
        patients.pop(patient_id, None)
        self._save(self._patients_file(), patients)
        
        set_cooldown(user_id, 'doctor', 'treat', 5)
        return {'reward': reward, 'exp_gain': exp_gain, 'patient': p, 'doctor': d}

    def _check_level_up(self, doctor: dict):
        """检查升级"""
        exp = doctor.get('experience', 0)
        current_rank = doctor.get('rank', '实习医生')
        
        ranks = list(DOCTOR_RANKS.keys())
        current_index = ranks.index(current_rank) if current_rank in ranks else 0
        
        if current_index < len(ranks) - 1:
            next_rank = ranks[current_index + 1]
            if exp >= DOCTOR_RANKS[next_rank]['requiredExp']:
                doctor['rank'] = next_rank
                doctor['level'] = DOCTOR_RANKS[next_rank]['level']
                doctor['salary'] = DOCTOR_RANKS[next_rank]['salary']
                return True
        return False

    # ========== 诊断系统 ==========

    def diagnose_patient(self, user_id: str, patient_id: str) -> dict:
        """诊断患者"""
        rem = check_cooldown(user_id, 'doctor', 'diagnose')
        if rem > 0:
            raise RuntimeError(f"cooldown:{rem}")
        
        patients = self._load(self._patients_file())
        p = patients.get(patient_id)
        if not p:
            raise ValueError('患者不存在')
        
        doctors = self._load(self._doctors_file())
        d = doctors.get(user_id)
        if not d:
            raise ValueError('你还不是医生')
        
        # 诊断能力影响准确率
        skills = d.get('skills', {})
        diagnosis_skill = skills.get('diagnosis', 50)
        base_accuracy = 50 + diagnosis_skill // 2
        accuracy = min(98, base_accuracy + random.randint(-10, 10))
        
        # 找到疾病信息
        diseases = self._load_diseases()
        disease_info = next((dis for dis in diseases if dis.get('name') == p.get('disease')), None)
        
        recommended_treatment = {}
        if disease_info:
            treatment = disease_info.get('treatment', {})
            recommended_treatment = {
                'medicines': treatment.get('medicines', []),
                'surgery': treatment.get('surgery'),
                'rest_days': treatment.get('rest_days', 3),
                'special_care': treatment.get('special_care', '')
            }
        
        # 更新患者诊断状态
        p['diagnosed'] = True
        p['treatment'] = recommended_treatment
        patients[patient_id] = p
        self._save(self._patients_file(), patients)
        
        # 增加经验
        exp_gain = 20 + p.get('severity', 1) * 5
        d['experience'] = d.get('experience', 0) + exp_gain
        self._check_level_up(d)
        doctors[user_id] = d
        self._save(self._doctors_file(), doctors)
        
        set_cooldown(user_id, 'doctor', 'diagnose', 10)
        
        return {
            'patient': p,
            'accuracy': accuracy,
            'recommended_treatment': recommended_treatment,
            'exp_gain': exp_gain
        }

    # ========== 开药系统 ==========

    def prescribe_medicine(self, user_id: str, patient_id: str, medicine_id: int) -> dict:
        """给患者开药"""
        rem = check_cooldown(user_id, 'doctor', 'prescribe')
        if rem > 0:
            raise RuntimeError(f"cooldown:{rem}")
        
        patients = self._load(self._patients_file())
        p = patients.get(patient_id)
        if not p:
            raise ValueError('患者不存在')
        
        doctors = self._load(self._doctors_file())
        d = doctors.get(user_id)
        if not d:
            raise ValueError('你还不是医生')
        
        medicines = self._load_medicines()
        medicine = next((m for m in medicines if m.get('id') == medicine_id), None)
        if not medicine:
            raise ValueError('药品不存在')
        
        # 计算有效性
        skills = d.get('skills', {})
        prescription_skill = skills.get('prescription', 40)
        base_effectiveness = medicine.get('effectiveness', 70)
        effectiveness = min(95, base_effectiveness + prescription_skill // 5)
        
        # 检查药物是否适用
        disease_name = p.get('disease', '')
        symptoms = p.get('symptoms', [])
        applications = medicine.get('application', [])
        
        is_suitable = any(
            app in disease_name or app in ' '.join(symptoms)
            for app in applications
        )
        
        if is_suitable:
            effectiveness += 15
        else:
            effectiveness -= 20
        
        effectiveness = max(10, min(95, effectiveness))
        
        # 治疗结果
        success = random.randint(1, 100) <= effectiveness
        
        reward = 0
        exp_gain = 15
        if success:
            reward = p.get('severity', 1) * 30 + 50
            exp_gain = 30
            # 移除患者
            patients.pop(patient_id, None)
        
        # 更新医生数据
        d['experience'] = d.get('experience', 0) + exp_gain
        self._check_level_up(d)
        doctors[user_id] = d
        self._save(self._doctors_file(), doctors)
        self._save(self._patients_file(), patients)
        
        if reward > 0:
            user = self.dm.load_user(user_id) or {}
            user['money'] = user.get('money', 0) + reward
            self.dm.save_user(user_id, user)
        
        set_cooldown(user_id, 'doctor', 'prescribe', 15)
        
        return {
            'medicine': medicine,
            'effectiveness': effectiveness,
            'success': success,
            'reward': reward,
            'exp_gain': exp_gain,
            'patient': p
        }

    # ========== 手术系统 ==========

    def perform_surgery(self, user_id: str, patient_id: str, surgery_id: int) -> dict:
        """执行手术"""
        rem = check_cooldown(user_id, 'doctor', 'surgery')
        if rem > 0:
            raise RuntimeError(f"cooldown:{rem}")
        
        patients = self._load(self._patients_file())
        p = patients.get(patient_id)
        if not p:
            raise ValueError('患者不存在')
        
        doctors = self._load(self._doctors_file())
        d = doctors.get(user_id)
        if not d:
            raise ValueError('你还不是医生')
        
        surgeries = self._load_surgeries()
        surgery = next((s for s in surgeries if s.get('id') == surgery_id), None)
        if not surgery:
            raise ValueError('手术类型不存在')
        
        # 检查等级要求
        required_level = surgery.get('required_level', 1)
        doctor_level = d.get('level', 1)
        if doctor_level < required_level:
            raise ValueError(f"需要达到{required_level}级才能执行此手术")
        
        # 计算成功率
        skills = d.get('skills', {})
        surgery_skill = skills.get('surgery', 30)
        base_success = surgery.get('success_rate', 70)
        
        success_rate = base_success + (surgery_skill - 50) // 2 + (doctor_level - required_level) * 5
        
        # 患者状况影响
        condition = p.get('condition', '轻症')
        if condition == '危重':
            success_rate -= 15
        elif condition == '重症':
            success_rate -= 5
        
        success_rate = max(5, min(95, success_rate))
        success = random.randint(1, 100) <= success_rate
        
        # 结果处理
        exp_gain = surgery.get('exp_reward', 100)
        reward = surgery.get('reward', 500)
        reputation_change = 0
        
        if success:
            reward = int(reward * 1.5)
            exp_gain = int(exp_gain * 1.5)
            reputation_change = 5
            outcome = "手术成功，患者恢复良好"
            
            # 更新统计
            if 'stats' not in d:
                d['stats'] = {}
            d['stats']['surgeries_performed'] = d['stats'].get('surgeries_performed', 0) + 1
            d['stats']['lives_saved'] = d['stats'].get('lives_saved', 0) + 1
            
            # 移除患者
            patients.pop(patient_id, None)
        else:
            reward = reward // 4
            exp_gain = exp_gain // 2
            reputation_change = -3
            outcome = "手术出现并发症，患者需要进一步治疗"
            
            if 'stats' not in d:
                d['stats'] = {}
            d['stats']['mistakes_made'] = d['stats'].get('mistakes_made', 0) + 1
        
        # 更新医生数据
        d['experience'] = d.get('experience', 0) + exp_gain
        hospital = d.get('hospital', {})
        hospital['reputation'] = max(0, min(100, hospital.get('reputation', 50) + reputation_change))
        d['hospital'] = hospital
        self._check_level_up(d)
        
        doctors[user_id] = d
        self._save(self._doctors_file(), doctors)
        self._save(self._patients_file(), patients)
        
        # 发放奖励
        user = self.dm.load_user(user_id) or {}
        user['money'] = user.get('money', 0) + reward
        self.dm.save_user(user_id, user)
        
        set_cooldown(user_id, 'doctor', 'surgery', 120)
        
        return {
            'surgery': surgery,
            'success': success,
            'success_rate': success_rate,
            'outcome': outcome,
            'reward': reward,
            'exp_gain': exp_gain,
            'reputation_change': reputation_change,
            'patient': p
        }

    # ========== 培训系统 ==========

    def doctor_training(self, user_id: str, skill_type: str) -> dict:
        """医生培训"""
        rem = check_cooldown(user_id, 'doctor', 'train')
        if rem > 0:
            raise RuntimeError(f"cooldown:{rem}")
        
        doctors = self._load(self._doctors_file())
        d = doctors.get(user_id)
        if not d:
            raise ValueError('你还不是医生')
        
        skill_mapping = {
            '诊断': 'diagnosis',
            '手术': 'surgery',
            '开药': 'prescription',
            '沟通': 'communication',
            '研究': 'research'
        }
        
        skill_key = skill_mapping.get(skill_type)
        if not skill_key:
            raise ValueError(f"无效的培训类型，可选: {', '.join(skill_mapping.keys())}")
        
        skills = d.get('skills', {})
        current_level = skills.get(skill_key, 50)
        
        if current_level >= 100:
            raise ValueError('该技能已达到最高等级')
        
        # 培训费用
        train_cost = 500 + current_level * 10
        user = self.dm.load_user(user_id) or {}
        if user.get('money', 0) < train_cost:
            raise ValueError('金币不足')
        
        # 成功率
        success_rate = 80 - (current_level - 50) // 2
        success = random.randint(1, 100) <= success_rate
        
        user['money'] -= train_cost
        self.dm.save_user(user_id, user)
        
        exp_gain = 0
        if success:
            skills[skill_key] = current_level + random.randint(3, 8)
            exp_gain = 50
            d['experience'] = d.get('experience', 0) + exp_gain
            if 'stats' not in d:
                d['stats'] = {}
            d['stats']['training_completed'] = d['stats'].get('training_completed', 0) + 1
        
        d['skills'] = skills
        self._check_level_up(d)
        doctors[user_id] = d
        self._save(self._doctors_file(), doctors)
        
        set_cooldown(user_id, 'doctor', 'train', 60)
        
        return {
            'skill_type': skill_type,
            'old_level': current_level,
            'new_level': skills[skill_key],
            'success': success,
            'cost': train_cost,
            'exp_gain': exp_gain
        }

    # ========== 医学研究 ==========

    def start_research(self, user_id: str, project_name: str) -> dict:
        """开始医学研究"""
        rem = check_cooldown(user_id, 'doctor', 'research')
        if rem > 0:
            raise RuntimeError(f"cooldown:{rem}")
        
        doctors = self._load(self._doctors_file())
        d = doctors.get(user_id)
        if not d:
            raise ValueError('你还不是医生')
        
        if d.get('research_project'):
            raise ValueError('你已有进行中的研究项目')
        
        # 研究项目配置
        projects = {
            '新药研发': {'skill_req': 30, 'exp': 500, 'money': 5000, 'desc': '研发新型药物'},
            '手术技术': {'skill_req': 40, 'exp': 600, 'money': 6000, 'desc': '改进手术技术'},
            '疾病预防': {'skill_req': 25, 'exp': 400, 'money': 4000, 'desc': '疾病预防研究'},
            '基因治疗': {'skill_req': 60, 'exp': 1000, 'money': 10000, 'desc': '基因治疗研究'}
        }
        
        project = projects.get(project_name)
        if not project:
            raise ValueError(f"无效的研究项目，可选: {', '.join(projects.keys())}")
        
        skills = d.get('skills', {})
        if skills.get('research', 20) < project['skill_req']:
            raise ValueError(f"研究能力不足，需要{project['skill_req']}点")
        
        d['research_project'] = {
            'name': project_name,
            'progress': 0,
            'exp_reward': project['exp'],
            'money_reward': project['money'],
            'started_at': datetime.utcnow().isoformat()
        }
        
        doctors[user_id] = d
        self._save(self._doctors_file(), doctors)
        
        set_cooldown(user_id, 'doctor', 'research', 60)
        
        return {'project': d['research_project']}

    def advance_research(self, user_id: str) -> dict:
        """推进研究进度"""
        rem = check_cooldown(user_id, 'doctor', 'advance')
        if rem > 0:
            raise RuntimeError(f"cooldown:{rem}")
        
        doctors = self._load(self._doctors_file())
        d = doctors.get(user_id)
        if not d:
            raise ValueError('你还不是医生')
        
        project = d.get('research_project')
        if not project:
            raise ValueError('没有进行中的研究项目')
        
        skills = d.get('skills', {})
        research_skill = skills.get('research', 20)
        
        # 进度增加
        progress_gain = 10 + research_skill // 10 + random.randint(0, 10)
        project['progress'] = min(100, project['progress'] + progress_gain)
        
        completed = project['progress'] >= 100
        result = {
            'project_name': project['name'],
            'progress': project['progress'],
            'progress_gain': progress_gain,
            'completed': completed
        }
        
        if completed:
            # 完成研究
            exp_gain = project.get('exp_reward', 500)
            money_gain = project.get('money_reward', 5000)
            
            d['experience'] = d.get('experience', 0) + exp_gain
            if 'stats' not in d:
                d['stats'] = {}
            d['stats']['research_completed'] = d['stats'].get('research_completed', 0) + 1
            
            user = self.dm.load_user(user_id) or {}
            user['money'] = user.get('money', 0) + money_gain
            self.dm.save_user(user_id, user)
            
            d['research_project'] = None
            self._check_level_up(d)
            
            result['exp_gain'] = exp_gain
            result['money_gain'] = money_gain
        else:
            d['research_project'] = project
        
        doctors[user_id] = d
        self._save(self._doctors_file(), doctors)
        
        set_cooldown(user_id, 'doctor', 'advance', 30)
        
        return result

    # ========== 医生排行榜 ==========

    def get_doctor_ranking(self, rank_type: str = 'exp') -> List[dict]:
        """获取医生排行榜"""
        doctors = self._load(self._doctors_file())
        
        rankings = []
        for uid, data in doctors.items():
            stats = data.get('stats', {})
            rankings.append({
                'user_id': uid,
                'name': data.get('name', '未知'),
                'rank': data.get('rank', '实习医生'),
                'experience': data.get('experience', 0),
                'patients_treated': stats.get('patients_treated', 0),
                'surgeries': stats.get('surgeries_performed', 0),
                'lives_saved': stats.get('lives_saved', 0)
            })
        
        if rank_type == 'exp':
            rankings.sort(key=lambda x: x['experience'], reverse=True)
        elif rank_type == 'patients':
            rankings.sort(key=lambda x: x['patients_treated'], reverse=True)
        elif rank_type == 'surgeries':
            rankings.sort(key=lambda x: x['surgeries'], reverse=True)
        
        return rankings[:20]

    # ========== 获取可用药品/手术列表 ==========

    def get_medicines_list(self) -> List[dict]:
        """获取药品列表"""
        return self._load_medicines()

    def get_surgeries_list(self) -> List[dict]:
        """获取手术列表"""
        return self._load_surgeries()

    def get_diseases_list(self) -> List[dict]:
        """获取疾病列表"""
        return self._load_diseases()
