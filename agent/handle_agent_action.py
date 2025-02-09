import constants
import re
from db.wallet import get_wallet_info
from web3 import Web3
from decimal import Decimal
import json
import logging
from typing import Optional
from trading.uniswap_client import UniswapClient
from trading.operations import TradingOperations

logger = logging.getLogger(__name__)

def execute_trade(
    uniswap_client: UniswapClient,
    trading_ops: TradingOperations,
    token_in: str,
    token_out: str,
    amount_in: Decimal,
    min_amount_out: Decimal,
    wallet_address: str
) -> Optional[str]:
    """
    Execute a trade between two tokens using Uniswap.
    Returns the transaction hash if successful, None otherwise.
    """
    try:
        # First estimate gas to ensure the trade is possible
        gas_estimate = uniswap_client.estimate_gas(
            token_in,
            token_out,
            amount_in,
            wallet_address
        )
        
        if gas_estimate == 0:
            logger.error("Failed to estimate gas, trade may not be possible")
            return None
            
        # Execute the trade
        tx_hash = uniswap_client.execute_trade(
            token_in,
            token_out,
            amount_in,
            min_amount_out,
            wallet_address
        )
        
        if tx_hash:
            # Record the trade in the database
            trading_ops.record_trade(
                wallet_address=wallet_address,
                token_in=token_in,
                token_out=token_out,
                amount_in=str(amount_in),
                min_amount_out=str(min_amount_out),
                tx_hash=tx_hash,
                gas_price=str(Web3.from_wei(gas_estimate, 'gwei')),
                status='PENDING'
            )
            
            logger.info(f"Trade executed successfully. Transaction hash: {tx_hash}")
            return tx_hash
        else:
            logger.error("Trade execution failed")
            return None

    except Exception as e:
        logger.error(f"Trade execution failed: {str(e)}")
        return None

def handle_agent_action(agent_action: str, content: str) -> None:
    """
    Handle various agent actions including trade execution and monitoring.
    """
    try:
        if agent_action == constants.TRADE_USDC_FOR_BTC:
            amount = Decimal(re.search(r'\d+', content).group())
            execute_trade(
                UniswapClient(),
                TradingOperations(),
                "USDC",
                "BTC",
                amount,
                amount * Decimal('0.99'),  # 1% slippage
                json.loads(get_wallet_info())["wallet_id"]
            )

        elif agent_action == constants.TRADE_USDC_FOR_ETH:
            amount = Decimal(re.search(r'\d+', content).group())
            execute_trade(
                UniswapClient(),
                TradingOperations(),
                "USDC",
                "ETH",
                amount,
                amount * Decimal('0.99'),  # 1% slippage
                json.loads(get_wallet_info())["wallet_id"]
            )

        elif agent_action == "check_trade_status":
            # Extract transaction hash from content
            tx_hash = re.search(r'0x[a-fA-F0-9]{64}', content)
            if tx_hash:
                trading_ops = TradingOperations()
                status = trading_ops.get_trade_status(tx_hash.group())
                logger.info(f"Trade status for {tx_hash.group()}: {status}")

        elif agent_action == "monitor_price":
            # Extract token address from content
            token_address = re.search(r'0x[a-fA-F0-9]{40}', content)
            if token_address:
                uniswap_client = UniswapClient()
                price = uniswap_client.get_token_price(token_address.group())
                trading_ops = TradingOperations()
                trading_ops.record_price(token_address.group(), str(price))
                logger.info(f"Recorded price for {token_address.group()}: {price} ETH")

    except Exception as e:
        logger.error(f"Error handling agent action {agent_action}: {str(e)}")
