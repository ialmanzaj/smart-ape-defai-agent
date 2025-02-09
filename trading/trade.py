import json
import time
from collections.abc import Callable
from decimal import Decimal
from pathlib import Path
from typing import Dict, Optional

from cdp import Asset, Wallet
from pydantic import BaseModel, Field
from web3 import Web3

from cdp_agentkit_core.actions import CdpAction

# Load ABIs
def load_abi(filename: str) -> Dict:
    abi_path = Path(__file__).parent / "abi" / filename
    with open(abi_path) as f:
        return json.load(f)

UNISWAP_ROUTER_ABI = load_abi("UniswapV3Router.json")
UNISWAP_FACTORY_ABI = load_abi("UniswapV3Factory.json")
ERC20_ABI = load_abi("ERC20.json")

# Contract Addresses
UNISWAP_ROUTER = "0x3fC91A3afd70395Cd496C647d5a6CC9D4B2b7FAD"  # Base Sepolia Router
UNISWAP_FACTORY = "0x9323c1d6D800ed51Bd7C6B216cfBec678B7d0BC2"  # Base Sepolia Factory

def approve(wallet: Wallet, token_address: str, spender: str, amount: str) -> str:
    """Approve spender to spend tokens.
    
    Args:
        wallet: The wallet to approve from
        token_address: The token to approve
        spender: The address to approve (usually Uniswap router)
        amount: The amount to approve in atomic units
        
    Returns:
        str: Success message or error
    """
    try:
        # Check current allowance
        allowance_result = wallet.invoke_contract(
            contract_address=token_address,
            method="allowance",
            abi=ERC20_ABI,
            args=[wallet.address, spender]
        ).wait()
        
        current_allowance = int(allowance_result.return_value)
        amount_int = int(amount)
        
        if current_allowance >= amount_int:
            return "Already approved"
            
        # Approve exact amount
        approval = wallet.invoke_contract(
            contract_address=token_address,
            method="approve",
            abi=ERC20_ABI,
            args=[spender, amount]
        ).wait()
        
        if not approval.success:
            return f"Error: Approval failed - {approval.error}"
            
        return "Approved successfully"
        
    except Exception as e:
        return f"Error: {str(e)}"

def get_uniswap_quote(
    token_in_address: str,
    token_out_address: str,
    amount_in: str,
    fee: int = 3000
) -> str:
    """Get quote for swap from Uniswap.
    
    Args:
        token_in_address: Address of input token
        token_out_address: Address of output token
        amount_in: Amount of input token in atomic units
        fee: Pool fee tier (default 0.3%)
        
    Returns:
        str: Expected output amount in atomic units
    """
    try:
        # Connect to Base Sepolia
        w3 = Web3(Web3.HTTPProvider("https://sepolia.base.org"))
        
        # Create contract instance
        router = w3.eth.contract(
            address=w3.to_checksum_address(UNISWAP_ROUTER),
            abi=UNISWAP_ROUTER_ABI
        )
        
        # Get quote
        quote = router.functions.quoteExactInputSingle(
            token_in_address,
            token_out_address,
            fee,
            amount_in,
            0  # No price limit
        ).call()
        
        return str(quote)
        
    except Exception as e:
        raise Exception(f"Failed to get quote: {str(e)}")

class UniswapSwapInput(BaseModel):
    """Input schema for Uniswap swap action."""

    token_in_address: str = Field(
        ..., 
        description="The address of the token to swap from"
    )
    token_out_address: str = Field(
        ..., 
        description="The address of the token to swap to"
    )
    amount_in: str = Field(
        ..., 
        description="The amount of input token to swap, in whole units"
    )
    recipient: str = Field(
        ...,
        description="The address that will receive the output tokens"
    )
    slippage: float = Field(
        default=0.5,
        description="Maximum allowed slippage percentage (default 0.5%)"
    )


SWAP_PROMPT = """
This tool allows swapping tokens using Uniswap V3 on Sepolia Base.
It takes:

- token_in_address: The address of the token you want to swap from
- token_out_address: The address of the token you want to swap to
- amount_in: The amount of input token to swap in whole units
    Examples:
    - 1 USDC
    - 0.1 ETH
    - 10 DAI
- recipient: The address to receive the output tokens
- slippage: Maximum allowed slippage percentage (optional, defaults to 0.5%)

Important notes:
- Make sure to use the exact amount provided. Do not convert units for amount_in.
- Please use token addresses (example 0x4200000000000000000000000000000000000006) for the token fields.
- The slippage parameter is optional and defaults to 0.5%.
- Ensure sufficient balance and approval before swapping.
"""


def swap_on_uniswap(
    wallet: Wallet,
    token_in_address: str,
    token_out_address: str,
    amount_in: str,
    recipient: str,
    slippage: float = 0.5,
) -> str:
    """Swap tokens using Uniswap V3 on Base Sepolia.

    Args:
        wallet (Wallet): The wallet to execute the swap from
        token_in_address (str): The address of the token to swap from
        token_out_address (str): The address of the token to swap to
        amount_in (str): The amount of input token to swap in whole units
        recipient (str): The address to receive the output tokens
        slippage (float): Maximum allowed slippage percentage

    Returns:
        str: A success message with transaction hash or error message
    """
    try:
        # Input validation
        if float(amount_in) <= 0:
            return "Error: Input amount must be greater than 0"
            
        # Convert input amount to atomic units
        token_in = Asset.fetch(wallet.network_id, token_in_address)
        atomic_amount_in = str(int(token_in.to_atomic_amount(Decimal(amount_in))))
        
        # Check balance
        balance_result = wallet.invoke_contract(
            contract_address=token_in_address,
            method="balanceOf",
            abi=ERC20_ABI,
            args=[wallet.address]
        ).wait()
        
        if not balance_result.success:
            return f"Error checking balance: {balance_result.error}"
            
        balance = int(balance_result.return_value)
        if balance < int(atomic_amount_in):
            return f"Error: Insufficient balance. Have {balance}, need {atomic_amount_in}"

        # Approve Uniswap router if needed
        approval_result = approve(wallet, token_in_address, UNISWAP_ROUTER, atomic_amount_in)
        if approval_result.startswith("Error"):
            return f"Error approving Uniswap Router as spender: {approval_result}"

        # Get quote and calculate minimum output
        try:
            quote = get_uniswap_quote(
                token_in_address,
                token_out_address,
                atomic_amount_in
            )
            min_amount_out = str(int(float(quote) * (1 - slippage / 100)))
        except Exception as e:
            return f"Error getting quote: {str(e)}"

        # Prepare swap parameters
        deadline = int(time.time() + 1800)  # 30 minutes from now
        
        swap_args = {
            "tokenIn": token_in_address,
            "tokenOut": token_out_address,
            "fee": 3000,  # 0.3% fee tier
            "recipient": recipient,
            "deadline": deadline,
            "amountIn": atomic_amount_in,
            "amountOutMinimum": min_amount_out,
            "sqrtPriceLimitX96": 0  # No price limit
        }

        # Estimate gas
        try:
            gas_estimate = wallet.estimate_gas(
                contract_address=UNISWAP_ROUTER,
                method="exactInputSingle",
                abi=UNISWAP_ROUTER_ABI,
                args=swap_args
            )
            if gas_estimate.error:
                return f"Error estimating gas: {gas_estimate.error}"
        except Exception as e:
            return f"Error estimating gas: {str(e)}"

        # Execute the swap
        try:
            invocation = wallet.invoke_contract(
                contract_address=UNISWAP_ROUTER,
                method="exactInputSingle",
                abi=UNISWAP_ROUTER_ABI,
                args=swap_args
            ).wait()

            if not invocation.success:
                return f"Error executing swap: {invocation.error}"

            # Format success message
            token_out = Asset.fetch(wallet.network_id, token_out_address)
            amount_out = token_out.from_atomic_amount(Decimal(min_amount_out))
            
            return (
                f"Successfully swapped {amount_in} {token_in.symbol} for at least "
                f"{amount_out} {token_out.symbol}\n"
                f"Transaction hash: {invocation.transaction_hash}\n"
                f"Transaction link: {invocation.transaction_link}"
            )

        except Exception as e:
            return f"Error executing swap: {str(e)}"

    except Exception as e:
        return f"Error in swap operation: {str(e)}"


class UniswapSwapAction(CdpAction):
    """Uniswap V3 swap action for Sepolia Base."""

    name: str = "uniswap_swap"
    description: str = SWAP_PROMPT
    args_schema: type[BaseModel] = UniswapSwapInput
    func: Callable[..., str] = swap_on_uniswap