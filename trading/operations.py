import sqlite3
import logging
from typing import List, Dict, Optional
from datetime import datetime
from web3 import Web3

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TradingOperations:
    def __init__(self):
        """Initialize trading operations with Uniswap client"""
       
        self.db_path = "agent.db"
        self.web3 = Web3(Web3.HTTPProvider("https://sepolia.base.org"))
    
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
        wallet_address: str,
        token_in: str,
        token_out: str,
        amount_in: str,
        min_amount_out: str,
        tx_hash: str,
        gas_price: str,
        status: str = 'PENDING'
    ) -> bool:
        """Record trade details in the database"""
        try:
            with sqlite3.connect(self.db_path) as con:
                cur = con.cursor()
                
                # Get wallet ID from wallet address
                cur.execute("SELECT id FROM wallet WHERE info LIKE ?", (f'%{wallet_address}%',))
                wallet_result = cur.fetchone()
                if not wallet_result:
                    logger.error(f"Wallet not found for address: {wallet_address}")
                    return False
                
                wallet_id = wallet_result[0]
                
                # Record the trade
                cur.execute("""
                    INSERT INTO trades 
                    (wallet_id, token_in, token_out, amount_in, min_amount_out, 
                     status, tx_hash, gas_price)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (wallet_id, token_in, token_out, amount_in, min_amount_out,
                      status, tx_hash, gas_price))
                con.commit()
                return True
        except Exception as e:
            logger.error(f"Error recording trade: {str(e)}")
            return False

    def get_trade_status(self, tx_hash: str) -> Optional[str]:
        """Get the current status of a trade"""
        try:
            # First check the database
            with sqlite3.connect(self.db_path) as con:
                cur = con.cursor()
                cur.execute("SELECT status FROM trades WHERE tx_hash = ?", (tx_hash,))
                result = cur.fetchone()
                
                if not result:
                    return None
                
                status = result[0]
                
                # If the status is PENDING, check the blockchain
                if status == 'PENDING':
                    receipt = self.web3.eth.get_transaction_receipt(tx_hash)
                    
                    if receipt:
                        # Update status based on receipt
                        new_status = 'COMPLETED' if receipt['status'] == 1 else 'FAILED'
                        
                        # Update database
                        cur.execute("""
                            UPDATE trades 
                            SET status = ? 
                            WHERE tx_hash = ?
                        """, (new_status, tx_hash))
                        con.commit()
                        
                        return new_status
                    else:
                        return 'PENDING'
                
                return status
                
        except Exception as e:
            logger.error(f"Error getting trade status: {str(e)}")
            return None

    def get_recent_trades(self, wallet_address: str, limit: int = 10) -> List[Dict]:
        """Get recent trades for a wallet"""
        try:
            with sqlite3.connect(self.db_path) as con:
                cur = con.cursor()
                
                # Get wallet ID from wallet address
                cur.execute("SELECT id FROM wallet WHERE info LIKE ?", (f'%{wallet_address}%',))
                wallet_result = cur.fetchone()
                if not wallet_result:
                    logger.error(f"Wallet not found for address: {wallet_address}")
                    return []
                
                wallet_id = wallet_result[0]
                
                # Get recent trades
                cur.execute("""
                    SELECT token_in, token_out, amount_in, min_amount_out,
                           status, tx_hash, gas_price, timestamp
                    FROM trades
                    WHERE wallet_id = ?
                    ORDER BY timestamp DESC
                    LIMIT ?
                """, (wallet_id, limit))
                
                trades = []
                for row in cur.fetchall():
                    trades.append({
                        'token_in': row[0],
                        'token_out': row[1],
                        'amount_in': row[2],
                        'min_amount_out': row[3],
                        'status': row[4],
                        'tx_hash': row[5],
                        'gas_price': row[6],
                        'timestamp': row[7]
                    })
                
                return trades
                
        except Exception as e:
            logger.error(f"Error getting recent trades: {str(e)}")
            return []

    def update_pending_trades(self) -> None:
        """Update the status of all pending trades"""
        try:
            with sqlite3.connect(self.db_path) as con:
                cur = con.cursor()
                
                # Get all pending trades
                cur.execute("SELECT tx_hash FROM trades WHERE status = 'PENDING'")
                pending_trades = cur.fetchall()
                
                for (tx_hash,) in pending_trades:
                    try:
                        receipt = self.web3.eth.get_transaction_receipt(tx_hash)
                        
                        if receipt:
                            # Update status based on receipt
                            new_status = 'COMPLETED' if receipt['status'] == 1 else 'FAILED'
                            
                            # Update database
                            cur.execute("""
                                UPDATE trades 
                                SET status = ? 
                                WHERE tx_hash = ?
                            """, (new_status, tx_hash))
                            
                            logger.info(f"Updated trade {tx_hash} status to {new_status}")
                    
                    except Exception as e:
                        logger.error(f"Error updating trade {tx_hash}: {str(e)}")
                        continue
                
                con.commit()
                
        except Exception as e:
            logger.error(f"Error updating pending trades: {str(e)}")

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