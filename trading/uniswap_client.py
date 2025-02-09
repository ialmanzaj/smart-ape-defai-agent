from typing import List, Dict, Optional
import logging
from web3 import Web3
from uniswap import Uniswap
from eth_account import Account
from eth_typing import Address
import os
from dotenv import load_dotenv
from cdp_sdk import CdpClient
from cdp_sdk.models import TransactionRequest

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class UniswapClient:
    def __init__(self):
        """Initialize Uniswap client with Base Sepolia configuration"""
        self.web3 = Web3(Web3.HTTPProvider(os.getenv('BASE_SEPOLIA_RPC_URL')))
        self.cdp_client = CdpClient()
        self.uniswap = Uniswap(
            address=None,  # Use CDP SDK wallet address
            private_key=None,  # Use CDP SDK for signing
            version=3,
            provider=self.web3,
            network='base-sepolia'
        )
        logger.info("Initialized Uniswap client on Base Sepolia")
    
    def get_token_price(self, token_address: str) -> float:
        """Get token price in terms of ETH"""
        try:
            price = self.uniswap.get_price_input(
                token_address,
                self.uniswap.get_weth_address(),
                10**18  # 1 token
            )
            return float(price) / (10**18)
        except Exception as e:
            logger.error(f"Error getting price for token {token_address}: {str(e)}")
            return 0.0
    
    def check_arbitrage_opportunity(
        self,
        token_path: List[str],
        amount_in: int
    ) -> Dict:
        """
        Check if there's an arbitrage opportunity in the given token path
        Returns dict with profit percentage and optimal input amount
        """
        try:
            # Simulate the trade through the path
            amounts = []
            current_amount = amount_in
            
            for i in range(len(token_path) - 1):
                amount_out = self.uniswap.get_price_output(
                    token_path[i],
                    token_path[i + 1],
                    current_amount
                )
                amounts.append(amount_out)
                current_amount = amount_out
            
            # Calculate profit/loss
            final_amount = amounts[-1]
            profit_percentage = ((final_amount - amount_in) / amount_in) * 100
            
            return {
                "profit_percentage": profit_percentage,
                "optimal_input": amount_in if profit_percentage > 0 else 0,
                "amounts": amounts
            }
        except Exception as e:
            logger.error(f"Error checking arbitrage: {str(e)}")
            return {
                "profit_percentage": 0,
                "optimal_input": 0,
                "amounts": []
            }
    
    def execute_trade(
        self,
        token_in: str,
        token_out: str,
        amount_in: int,
        min_amount_out: int,
        wallet_address: str
    ) -> Optional[str]:
        """Execute a trade using CDP SDK wallet"""
        try:
            # Get the swap data from Uniswap
            swap_data = self.uniswap.get_swap_data(
                token_in,
                token_out,
                amount_in,
                min_amount_out
            )
            
            # Create transaction request using CDP SDK
            tx_request = TransactionRequest(
                to=self.uniswap.router_address,
                data=swap_data,
                value=amount_in if token_in == self.uniswap.get_weth_address() else 0,
                gas_limit=300000  # Safe default, will be estimated
            )
            
            # Send transaction using CDP SDK
            tx_response = self.cdp_client.send_transaction(
                wallet_address=wallet_address,
                transaction=tx_request
            )
            
            logger.info(f"Trade executed: {amount_in} {token_in} -> {token_out}")
            logger.info(f"Transaction hash: {tx_response.hash}")
            
            return tx_response.hash
            
        except Exception as e:
            logger.error(f"Error executing trade: {str(e)}")
            return None
    
    def estimate_gas(
        self,
        token_in: str,
        token_out: str,
        amount_in: int,
        wallet_address: str
    ) -> int:
        """Estimate gas cost for a trade"""
        try:
            # Get the swap data from Uniswap
            swap_data = self.uniswap.get_swap_data(
                token_in,
                token_out,
                amount_in,
                0  # min_amount_out not needed for gas estimation
            )
            
            # Create transaction request
            tx_request = TransactionRequest(
                to=self.uniswap.router_address,
                data=swap_data,
                value=amount_in if token_in == self.uniswap.get_weth_address() else 0
            )
            
            # Estimate gas using CDP SDK
            gas_estimate = self.cdp_client.estimate_gas(
                wallet_address=wallet_address,
                transaction=tx_request
            )
            
            return gas_estimate
            
        except Exception as e:
            logger.error(f"Error estimating gas: {str(e)}")
            return 0 