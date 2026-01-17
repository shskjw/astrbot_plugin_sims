from .models import StockData, UserStockHold, PlayerCompany
from typing import Dict, List, Optional
import json
from pathlib import Path

class StockMarket:
    def __init__(self):
        self.stocks: Dict[str, StockData] = {}
        self.player_companies: Dict[str, PlayerCompany] = {} # Key: stock_id

    def register_stock(self, stock: StockData):
        self.stocks[stock.id] = stock

    def get_stock(self, stock_id: str) -> Optional[StockData]:
        # Check system stocks first
        if stock_id in self.stocks:
            return self.stocks.get(stock_id)
        # Check player companies
        if stock_id in self.player_companies:
            comp = self.player_companies[stock_id]
            # Convert to interface compatible StockData
            return StockData(id=comp.stock_id, name=comp.stock_name, price=comp.share_price, volatility=0.2)
        return None

    def ipo(self, data_manager, user_id: str, company_name: str, stock_name: str, initial_price: float):
        """Initial Public Offering for a player"""
        # User must have some assets (checked outside or loose requirement)
        # Check if user already has a company
        for pc in self.player_companies.values():
            if pc.owner_id == user_id:
                raise ValueError("你已经拥有一家上市企业了！")
        
        # Validations
        if initial_price < 1 or initial_price > 100:
            raise ValueError("发行价必须在 1-100 之间")

        stock_id = f"IPO_{user_id[:5]}" # Simple ID
        pc = PlayerCompany(
            owner_id=user_id,
            owner_name="Unknown", # Should fetch proper name
            company_name=company_name,
            stock_id=stock_id,
            stock_name=stock_name,
            share_price=initial_price
        )
        self.player_companies[stock_id] = pc
        # In a real persistence scenario: should save to disk
        # saving self.player_companies to a file
        self._save_companies(data_manager)
        return pc

    def _save_companies(self, dm):
        path = Path(dm.root) / 'data' / 'stock'
        path.mkdir(parents=True, exist_ok=True)
        file = path / 'companies.json'
        data = [c.dict() for c in self.player_companies.values()]
        file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    
    def load_companies(self, dm):
        path = Path(dm.root) / 'data' / 'stock' / 'companies.json'
        if path.exists():
            try:
                raw = json.loads(path.read_text(encoding='utf-8'))
                for r in raw:
                    pc = PlayerCompany(**r)
                    self.player_companies[pc.stock_id] = pc
            except: 
                pass

    def buy(self, data_manager, user_id: str, stock_id: str, amount: int):
        stock = self.get_stock(stock_id)
        if not stock:
            raise ValueError("股票不存在")
        if amount <= 0:
            raise ValueError("购买数量必须大于0")
        
        # Check if player stock, limit by issued shares
        if stock_id in self.player_companies:
            pc = self.player_companies[stock_id]
            # Ideally we check available shares in market, simplified here:
            if amount > pc.issued_shares: # Simple check
               pass # Allow overbuy for now or implement market depth

        cost = stock.price * amount
        user = data_manager.load_user(user_id) or {}
        if user.get('money', 0) < cost:
            raise ValueError("金币不足")
        user['money'] = user.get('money', 0) - cost
        
        # If buying player stock, the money (IPO part) goes to system or owner?
        # Standard: Buying from market -> money to sellers.
        # Buying IPO -> money to owner.
        # Simplified: Money vanishes to system (liquidity pool)
        
        # update holdings in user record
        holdings = user.setdefault('stocks', {})
        cur = holdings.get(stock_id, {'amount':0, 'avg_price':0})
        total_cost = cur['avg_price'] * cur['amount'] + cost
        total_amount = cur['amount'] + amount
        cur['amount'] = total_amount
        cur['avg_price'] = total_cost / total_amount
        holdings[stock_id] = cur
        data_manager.save_user(user_id, user)
        
        # Influence price: Buying increases price slightly
        if stock_id in self.player_companies:
             pc = self.player_companies[stock_id]
             pc.share_price *= (1 + 0.001 * amount) # 0.1% per share
             self._save_companies(data_manager)

        return cur

    def sell(self, data_manager, user_id: str, stock_id: str, amount: int):
        stock = self.get_stock(stock_id)
        if not stock:
            raise ValueError("股票不存在")
        if amount <= 0:
            raise ValueError("出售数量必须大于0")
        user = data_manager.load_user(user_id) or {}
        holdings = user.get('stocks', {})
        cur = holdings.get(stock_id)
        if not cur or cur.get('amount',0) < amount:
            raise ValueError("持仓不足")
        revenue = stock.price * amount
        user['money'] = user.get('money', 0) + revenue
        
        # Influence price: Selling decreases price
        if stock_id in self.player_companies:
             pc = self.player_companies[stock_id]
             pc.share_price *= (1 - 0.001 * amount)
             if pc.share_price < 0.1: pc.share_price = 0.1
             self._save_companies(data_manager)

        cur['amount'] = cur.get('amount',0) - amount
        if cur['amount'] == 0:
            holdings.pop(stock_id, None)
        else:
            holdings[stock_id] = cur
        user['stocks'] = holdings
        data_manager.save_user(user_id, user)
        return {'revenue': revenue, 'remaining': cur.get('amount',0)}

    def list_holdings(self, data_manager, user_id: str):
        user = data_manager.load_user(user_id) or {}
        return user.get('stocks', {})

    def update_prices(self):
        # Simulate price changes using volatility
        for s in self.stocks.values():
            s.price = max(0.01, s.price * (1 + (s.volatility - 0.5) * 0.02))
