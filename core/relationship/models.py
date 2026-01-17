from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class Child:
    id: str
    name: str
    gender: str
    age: int = 0  # Days
    
    def to_dict(self):
        return self.__dict__

@dataclass
class Relationship:
    user_id: str
    target_id: str # NPC ID or User ID
    target_name: str
    status: str # pursuing, inRelationship, engaged, married
    affection: int = 0
    happiness: int = 0
    children: List[Child] = field(default_factory=list)
    start_date: str = ""

    def to_dict(self):
        data = self.__dict__.copy()
        data['children'] = [c.to_dict() for c in self.children]
        return data

    @classmethod
    def from_dict(cls, data):
        c_data = data.pop('children', [])
        inst = cls(**data)
        inst.children = [Child(**c) for c in c_data]
        return inst
