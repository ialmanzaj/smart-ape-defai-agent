import constants
import re
from db.wallet import get_wallet_info
from web3 import Web3
from decimal import Decimal
import json
import logging

logger = logging.getLogger(__name__)

def execute_trade(from_token: str, to_token: str, amount: Decimal) -> bool:
    """
    Execute a trade between two tokens using Uniswap.
    """
    try:
        # Connect to Base Sepolia
        w3 = Web3(Web3.HTTPProvider("https://sepolia.base.org"))
        if not w3.is_connected():
            raise Exception("Failed to connect to Base Sepolia")

        # Load wallet from AgentKit
        wallet_data = json.loads(get_wallet_info())
        wallet_address = wallet_data["wallet_id"]
        private_key = wallet_data["seed"]

        # Build transaction
        tx = {
            "from": wallet_address,
            "to": constants.UNISWAP_ROUTER_ADDRESS,
            "value": w3.to_wei(amount, 'ether'),
            "gas": 2000000,
            "gasPrice": w3.to_wei('10', 'gwei'),
            "nonce": w3.eth.get_transaction_count(wallet_address),
        }

        # Sign and send transaction
        signed_tx = w3.eth.account.sign_transaction(tx, private_key)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
        w3.eth.wait_for_transaction_receipt(tx_hash)

        logger.info(f"Trade executed: {amount} {from_token} -> {to_token}")
        return True

    except Exception as e:
        logger.error(f"Trade execution failed: {str(e)}")
        return False

def handle_agent_action(agent_action, content):
    """
    Adds handling for the agent action.
    In our sample app, we just add deployed tokens and NFTs to the database.
    """
    if agent_action == constants.TRADE_TOKEN:
        # Search for contract address from output
        address = re.search(r"0x[a-fA-F0-9]{40}", content).group()
        # Add token to database

    elif agent_action == constants.TRADE_USDC_FOR_BTC:
        amount = Decimal(re.search(r'\d+', content).group())
        execute_trade("USDC", "BTC", amount)

    elif agent_action == constants.TRADE_USDC_FOR_ETH:
        amount = Decimal(re.search(r'\d+', content).group())
        execute_trade("USDC", "ETH", amount)
