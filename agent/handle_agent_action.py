import constants
import re
from db.wallet import get_wallet_info
from web3 import Web3
from decimal import Decimal
import json
import logging
from typing import Optional

from trading.operations import TradingOperations

logger = logging.getLogger(__name__)


def handle_agent_action(agent_action: str, content: str) -> None:
    """
    Handle various agent actions including trade execution and monitoring.
    """
    try:
        if agent_action == constants.TRADE_USDC_FOR_BTC:
            amount = Decimal(re.search(r"\d+", content).group())

        elif agent_action == constants.TRADE_USDC_FOR_ETH:
            amount = Decimal(re.search(r"\d+", content).group())

        elif agent_action == "check_trade_status":
            # Extract transaction hash from content
            tx_hash = re.search(r"0x[a-fA-F0-9]{64}", content)
            if tx_hash:
                trading_ops = TradingOperations()
                status = trading_ops.get_trade_status(tx_hash.group())
                logger.info(f"Trade status for {tx_hash.group()}: {status}")

        elif agent_action == "monitor_price":
            # Extract token address from content
            token_address = re.search(r"0x[a-fA-F0-9]{40}", content)
            if token_address:
                pass

    except Exception as e:
        logger.error(f"Error handling agent action {agent_action}: {str(e)}")
