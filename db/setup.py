import sqlite3
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def setup():
    """
    Initialize database with proper table schemas including primary keys
    and appropriate constraints.
    """
    try:
        with sqlite3.connect("agent.db") as con:
            cur = con.cursor()
            
            # Wallet table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS wallet(
                    id INTEGER PRIMARY KEY,
                    info TEXT
                )
            """)
            
            # NFTs table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS nfts(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    contract TEXT UNIQUE NOT NULL
                )
            """)
            
            # ERC20s table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS erc20s(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    contract TEXT UNIQUE NOT NULL
                )
            """)
            
            # Trades table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS trades(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    wallet_id INTEGER,
                    token_in TEXT NOT NULL,
                    token_out TEXT NOT NULL,
                    amount_in TEXT NOT NULL,
                    min_amount_out TEXT NOT NULL,
                    status TEXT NOT NULL,
                    tx_hash TEXT UNIQUE,
                    gas_price TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(wallet_id) REFERENCES wallet(id)
                )
            """)
            
            # Price monitoring table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS price_monitoring(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    token_address TEXT NOT NULL,
                    price_usd TEXT NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Arbitrage opportunities table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS arbitrage_opportunities(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    token_path TEXT NOT NULL,
                    profit_percentage TEXT NOT NULL,
                    min_input_amount TEXT NOT NULL,
                    status TEXT NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            con.commit()
            logger.info("Database tables created successfully")
    except sqlite3.Error as e:
        logger.error(f"Failed to setup database: {str(e)}")
        raise