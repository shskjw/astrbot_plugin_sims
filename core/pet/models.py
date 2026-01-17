from dataclasses import dataclass, field
import uuid
from typing import List, Dict

@dataclass
class Pet:
    id: str
    owner_id: str
    name: str
    type: str # cat, dog, rabbit
    rarity: str # R, SR, SSR
    level: int = 1
    exp: int = 0
    hunger: int = 80 # 0-100
    mood: int = 80 # 0-100
    cleanliness: int = 80 # 0-100
    skills: List[str] = field(default_factory=list) # "RatHunter", "Guard"

    @property
    def max_exp(self):
        return self.level * 100

    def to_dict(self):
        return self.__dict__

    @classmethod
    def from_dict(cls, data):
        return cls(**data)
