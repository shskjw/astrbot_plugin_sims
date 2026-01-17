import json
import random
import uuid
from pathlib import Path
from typing import List, Optional
from ..common.data_manager import DataManager
from .models import Pet

class PetLogic:
    def __init__(self, data_manager: DataManager):
        self.dm = data_manager
        self.data_path = Path(self.dm.root) / 'data' / 'pet'
        self.data_path.mkdir(parents=True, exist_ok=True)
        self.pet_file = self.data_path / 'pets.json'
        
    def _load_pets(self) -> List[Pet]:
        if not self.pet_file.exists():
            return []
        try:
            data = json.loads(self.pet_file.read_text(encoding='utf-8'))
            return [Pet.from_dict(p) for p in data]
        except:
            return []

    def _save_pets(self, pets: List[Pet]):
        self.pet_file.write_text(json.dumps([p.to_dict() for p in pets], ensure_ascii=False, indent=2), encoding='utf-8')

    def get_user_pets(self, user_id: str) -> List[Pet]:
        all_pets = self._load_pets()
        return [p for p in all_pets if p.owner_id == user_id]

    def get_pet(self, pet_id: str) -> Optional[Pet]:
        all_pets = self._load_pets()
        for p in all_pets:
            if p.id == pet_id or str(p.id).startswith(pet_id): # Fuzzy match
                return p
        return None

    def draw_pet(self, user_id: str) -> Pet:
        # Simple gacha logic
        rarity_weights = {"R": 70, "SR": 25, "SSR": 5}
        rarity = random.choices(list(rarity_weights.keys()), weights=list(rarity_weights.values()))[0]
        
        types = ["猫", "狗", "兔子", "仓鼠"]
        p_type = random.choice(types)
        
        pet = Pet(
            id=str(uuid.uuid4())[:8],
            owner_id=user_id,
            name=f"{rarity}级{p_type}",
            type=p_type,
            rarity=rarity
        )
        
        pets = self._load_pets()
        pets.append(pet)
        self._save_pets(pets)
        return pet

    def feed_pet(self, pet_id: str, food_quality: int = 10):
        pets = self._load_pets()
        target = None
        for p in pets:
            if p.id == pet_id:
                target = p
                break
        
        if target:
            target.hunger = min(100, target.hunger + food_quality * 5)
            target.mood = min(100, target.mood + 2)
            target.exp += 15
            if target.exp >= target.max_exp:
                target.level += 1
                target.exp = 0
            self._save_pets(pets)
            return target
        return None

    def interact_pet(self, pet_id: str):
        pets = self._load_pets()
        target = None
        for p in pets:
            if p.id == pet_id:
                target = p
                break
        
        if target:
            target.mood = min(100, target.mood + 15)
            target.exp += 10
            if target.exp >= target.max_exp:
                target.level += 1
                target.exp = 0
            self._save_pets(pets)
            return target
        return None
