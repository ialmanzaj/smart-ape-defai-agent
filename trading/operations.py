import sqlite3
import logging
from typing import List, Dict, Optional
from datetime import datetime
from .uniswap_client import UniswapClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TradingOperations:
    def __init__(self):
        """Initialize trading operations with Uniswap client"""
        self.uniswap = UniswapClient()
        self.db_path = "agent.db"
    
    def record_price(self, token_address: str, price_usd: str) -> bool:
        """Record token price in the database"""
        try:
            with sqlite3.connect(self.db_path) as con:
                cur = con.cursor()
                cur.execute("""
                    INSERT INTO price_monitoring (token_address, price_usd)
                    VALUES (?, ?)
                """, (token_address, price_usd))
                con.commit()
                return True
        except Exception as e:
            logger.error(f"Error recording price: {str(e)}")
            return False
    
    def record_arbitrage_opportunity(
        self,
        token_path: str,
        profit_percentage: str,
        min_input_amount: str
    ) -> bool:
        """Record arbitrage opportunity in the database"""
        try:
            with sqlite3.connect(self.db_path) as con:
                cur = con.cursor()
                cur.execute("""
                    INSERT INTO arbitrage_opportunities 
                    (token_path, profit_percentage, min_input_amount, status)
                    VALUES (?, ?, ?, 'DETECTED')
                """, (token_path, profit_percentage, min_input_amount))
                con.commit()
                return True
        except Exception as e:
            logger.error(f"Error recording arbitrage opportunity: {str(e)}")
            return False
    
    def record_trade(
        self,
        wallet_id: int,
        token_in: str,
        token_out: str,
        amount_in: str,
        min_amount_out: str,
        tx_hash: Optional[str] = None,
        gas_price: Optional[str] = None
    ) -> bool:
        """Record trade in the database"""
        try:
            with sqlite3.connect(self.db_path) as con:
                cur = con.cursor()
                cur.execute("""
                    INSERT INTO trades 
                    (wallet_id, token_in, token_out, amount_in, min_amount_out, 
                     status, tx_hash, gas_price)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (wallet_id, token_in, token_out, amount_in, min_amount_out,
                     'PENDING' if tx_hash else 'FAILED', tx_hash, gas_price))
                con.commit()
                return True
        except Exception as e:
            logger.error(f"Error recording trade: {str(e)}")
            return False
    
    def update_trade_status(self, tx_hash: str, status: str) -> bool:
        """Update trade status in the database"""
        try:
            with sqlite3.connect(self.db_path) as con:
                cur = con.cursor()
                cur.execute("""
                    UPDATE trades 
                    SET status = ?
                    WHERE tx_hash = ?
                """, (status, tx_hash))
                con.commit()
                return True
        except Exception as e:
            logger.error(f"Error updating trade status: {str(e)}")
            return False
    
    def get_recent_trades(self, wallet_id: int, limit: int = 10) -> List[Dict]:
        """Get recent trades for a wallet"""
        try:
            with sqlite3.connect(self.db_path) as con:
                con.row_factory = sqlite3.Row
                cur = con.cursor()
                cur.execute("""
                    SELECT * FROM trades 
                    WHERE wallet_id = ?
                    ORDER BY timestamp DESC
                    LIMIT ?
                """, (wallet_id, limit))
                return [dict(row) for row in cur.fetchall()]
        except Exception as e:
            logger.error(f"Error getting recent trades: {str(e)}")
            return []
    
    def get_active_arbitrage_opportunities(self) -> List[Dict]:
        """Get active arbitrage opportunities"""
        try:
            with sqlite3.connect(self.db_path) as con:
                con.row_factory = sqlite3.Row
                cur = con.cursor()
                cur.execute("""
                    SELECT * FROM arbitrage_opportunities 
                    WHERE status = 'DETECTED'
                    ORDER BY profit_percentage DESC
                """)
                return [dict(row) for row in cur.fetchall()]
        except Exception as e:
            logger.error(f"Error getting arbitrage opportunities: {str(e)}")
            return [] 