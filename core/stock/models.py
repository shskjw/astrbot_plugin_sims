from pydantic import BaseModel

class StockData(BaseModel):
    id: str
    name: str
    price: float
    volatility: float
    last_update: int = 0

class UserStockHold(BaseModel):
    user_id: str
    stock_id: str
    amount: int
    avg_price: float

class PlayerCompany(BaseModel):
    owner_id: str
    owner_name: str
    company_name: str
    stock_id: str # e.g. "USER_12345"
    stock_name: str # e.g. "XXX的农场"
    total_shares: int = 10000
    issued_shares: int = 1000 # Shares in market
    share_price: float = 10.0
    dividend_rate: float = 0.05
    description: str = ""

