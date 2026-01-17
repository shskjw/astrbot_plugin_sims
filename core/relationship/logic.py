import json
from pathlib import Path
from typing import List, Optional, Dict
from ..common.data_manager import DataManager
from .models import Relationship, Child

class RelationshipLogic:
    def __init__(self, data_manager: DataManager):
        self.dm = data_manager
        self.data_path = Path(self.dm.root) / 'data' / 'relationship'
        self.data_path.mkdir(parents=True, exist_ok=True)
        self.rel_file = self.data_path / 'relationships.json'

    def _load_all(self) -> Dict[str, List[Relationship]]:
        if not self.rel_file.exists():
            return {}
        try:
            raw = json.loads(self.rel_file.read_text(encoding='utf-8'))
            res = {}
            for uid, rels in raw.items():
                res[uid] = [Relationship.from_dict(r) for r in rels]
            return res
        except:
            return {}

    def _save_all(self, data: Dict[str, List[Relationship]]):
        serializable = {
            uid: [r.to_dict() for r in rels]
            for uid, rels in data.items()
        }
        self.rel_file.write_text(json.dumps(serializable, ensure_ascii=False, indent=2), encoding='utf-8')

    def get_relationship(self, user_id: str, target_id: str) -> Optional[Relationship]:
        all_data = self._load_all()
        user_rels = all_data.get(user_id, [])
        for r in user_rels:
            if r.target_id == target_id:
                return r
        return None

    def add_affection(self, user_id: str, target_id: str, target_name: str, amount: int):
        all_data = self._load_all()
        user_rels = all_data.get(user_id, [])
        
        target = None
        for r in user_rels:
            if r.target_id == target_id:
                target = r
                break
        
        if not target:
            target = Relationship(
                user_id=user_id, 
                target_id=target_id, 
                target_name=target_name, 
                status="pursuing",
                affection=0
            )
            user_rels.append(target)
        
        target.affection += amount
        if target.affection >= 100 and target.status == "pursuing":
            target.status = "inRelationship" # Auto upgrade for simplicity
        
        all_data[user_id] = user_rels
        self._save_all(all_data)
        return target

    def check_marriage(self, user_id: str, target_id: str):
        rel = self.get_relationship(user_id, target_id)
        if rel and rel.affection >= 500 and rel.status != "married":
            return True, rel
        return False, rel

    def marry(self, user_id: str, target_id: str):
        all_data = self._load_all()
        user_rels = all_data.get(user_id, [])
        
        target = None
        for r in user_rels:
            if r.target_id == target_id:
                target = r
                break
        
        if target:
            target.status = "married"
            target.happiness = 100
            all_data[user_id] = user_rels
            self._save_all(all_data)
        return target
