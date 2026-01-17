from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class DoctorSkills(BaseModel):
    """医生技能"""
    diagnosis: int = 50      # 诊断能力
    surgery: int = 30        # 手术能力
    prescription: int = 40   # 开药能力
    communication: int = 60  # 沟通能力
    research: int = 20       # 研究能力

class DoctorStats(BaseModel):
    """医生统计数据"""
    patients_treated: int = 0
    surgeries_performed: int = 0
    research_completed: int = 0
    training_completed: int = 0
    lives_saved: int = 0
    mistakes_made: int = 0

class HospitalInfo(BaseModel):
    """医院信息"""
    name: str = "社区卫生服务中心"
    level: int = 1
    reputation: int = 50
    max_patients: int = 50
    equipment: List[Dict[str, Any]] = Field(default_factory=list)
    departments: List[str] = Field(default_factory=lambda: ["全科"])

class DoctorInfo(BaseModel):
    user_id: str
    name: str = "医生"
    rank: str = "实习医生"
    level: int = 1
    experience: int = 0
    experience_needed: int = 1000
    salary: int = 5000
    patients_seen: int = 0
    skills: DoctorSkills = Field(default_factory=DoctorSkills)
    stats: DoctorStats = Field(default_factory=DoctorStats)
    hospital: HospitalInfo = Field(default_factory=HospitalInfo)
    specialty: Optional[str] = None
    certifications: List[str] = Field(default_factory=lambda: ["基础医疗执照"])
    current_patients: List[Dict[str, Any]] = Field(default_factory=list)
    research_project: Optional[Dict[str, Any]] = None

class Patient(BaseModel):
    id: str
    name: str
    age: int = 30
    gender: str = "未知"
    disease: str
    disease_id: Optional[int] = None
    severity: int = 1        # 1-10
    condition: str = "轻症"  # 轻症/重症/危重
    symptoms: List[str] = Field(default_factory=list)
    diagnosed: bool = False
    treatment: Optional[Dict[str, Any]] = None
    satisfaction: int = 70
    admitted_at: Optional[str] = None

class Hospital(BaseModel):
    id: str
    name: str
    level: int = 1
    funds: int = 0
    staff_count: int = 0
    reputation: int = 50

# ========== 医生等级配置 ==========

DOCTOR_RANKS = {
    "实习医生": {"level": 1, "salary": 5000, "requiredExp": 0},
    "住院医师": {"level": 2, "salary": 8000, "requiredExp": 1000},
    "主治医师": {"level": 3, "salary": 15000, "requiredExp": 3000},
    "副主任医师": {"level": 4, "salary": 25000, "requiredExp": 8000},
    "主任医师": {"level": 5, "salary": 40000, "requiredExp": 15000}
}

# ========== 诊断结果 ==========

class DiagnosisResult(BaseModel):
    """诊断结果"""
    patient_id: str
    disease_name: str
    accuracy: float
    recommended_treatment: Dict[str, Any] = Field(default_factory=dict)
    exp_gained: int = 0

# ========== 手术结果 ==========

class SurgeryResult(BaseModel):
    """手术结果"""
    patient_id: str
    surgery_name: str
    success: bool
    outcome: str
    exp_gained: int = 0
    money_earned: int = 0
    reputation_change: int = 0

# ========== 研究项目 ==========

class ResearchProject(BaseModel):
    """研究项目"""
    id: str
    name: str
    description: str
    progress: int = 0        # 0-100
    required_skill: int = 30
    reward_exp: int = 500
    reward_money: int = 5000
    started_at: Optional[str] = None
