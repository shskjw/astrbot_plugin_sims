from pydantic import BaseModel

class Property(BaseModel):
    id: str
    name: str
    price: float
    rent: float
    owner_id: str = None

class UserProperty(BaseModel):
    user_id: str
    property_id: str
    level: int = 1
