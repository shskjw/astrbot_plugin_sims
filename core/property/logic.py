from .models import Property
from typing import Dict

class PropertyMarket:
    def __init__(self):
        self.properties: Dict[str, Property] = {}

    def register_property(self, prop: Property):
        self.properties[prop.id] = prop

    def buy_property(self, user_id: str, prop_id: str):
        prop = self.properties.get(prop_id)
        if not prop:
            raise ValueError("房产不存在")
        if prop.owner_id is not None:
            raise ValueError("房产已被购买")
        prop.owner_id = user_id
        return True

    def collect_rent(self):
        # placeholder for rent collection
        return sum(p.rent for p in self.properties.values() if p.owner_id)
