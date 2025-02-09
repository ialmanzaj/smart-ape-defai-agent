import json
import logging
import time
from collections.abc import Callable
from decimal import Decimal
from pathlib import Path
from typing import Dict, Optional

from cdp import Asset, Wallet
from pydantic import BaseModel, Field
from web3 import Web3

from cdp_agentkit_core.actions import CdpAction

logger = logging.getLogger(__name__)


# Load ABIs
def load_abi(filename: str) -> Dict:
    abi_path = Path(__file__).parent / "abi" / filename
    with open(abi_path) as f:
        return json.load(f)


UNISWAP_ROUTER_ABI = load_abi("UniswapV3Router.json")
UNISWAP_FACTORY_ABI = load_abi("UniswapV3Factory.json")
ERC20_ABI = load_abi("ERC20.json")

# Contract Addresses
UNISWAP_ROUTER = "0x94cC0AaC535CCDB3C01d6787D6413C739ae12bc4"  # Base Sepolia Router
UNISWAP_FACTORY = "0x4752ba5DBc23f44D87826276BF6Fd6b1C372aD24"  # Base Sepolia Factory


def approve(wallet: Wallet, user_address: str, token_address: str, spender: str, amount: str) -> str:
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
            args=[user_address, spender],
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
            args=[spender, amount],
        ).wait()

        if not approval.success:
            return f"Error: Approval failed - {approval.error}"

        return "Approved successfully"

    except Exception as e:
        return f"Error: {str(e)}"


def get_uniswap_quote(
    token_in_address: str, token_out_address: str, amount_in: str, fee: int = 3000
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
            address=w3.to_checksum_address(UNISWAP_ROUTER), abi=UNISWAP_ROUTER_ABI
        )

        # Get quote
        quote = router.functions.quoteExactInputSingle(
            token_in_address, token_out_address, fee, amount_in, 0  # No price limit
        ).call()

        return str(quote)

    except Exception as e:
        raise Exception(f"Failed to get quote: {str(e)}")


class UniswapSwapInput(BaseModel):
    """Input schema for Uniswap swap action."""

    token_in_address: str = Field(
        ..., description="The address of the token to swap from"
    )
    token_out_address: str = Field(
        ..., description="The address of the token to swap to"
    )
    amount_in: str = Field(
        ..., description="The amount of input token to swap, in whole units"
    )
    recipient: str = Field(
        ..., description="The address that will receive the output tokens"
    )
    slippage: float = Field(
        default=0.5, description="Maximum allowed slippage percentage (default 0.5%)"
    )


SWAP_PROMPT = """Swap tokens using Uniswap V3 on Base Sepolia.

Required Parameters:
- token_in_address: Token to swap from
  • USDC: 0x036CbD53842c5426634e7929541eC2318f3dCF7e
  • ETH/WETH: 0x4200000000000000000000000000000000000006
- token_out_address: Token to swap to (use addresses above)
- amount_in: Amount to swap (e.g., "0.1" ETH or "100" USDC)
- recipient: Address to receive tokens (optional, defaults to sender)
- slippage: Max price slippage % (optional, default 0.5%)

Examples:
1. USDC→ETH: {"token_in_address": "0x036CbD53842c5426634e7929541eC2318f3dCF7e", "token_out_address": "0x4200000000000000000000000000000000000006", "amount_in": "100"}
2. ETH→USDC: {"token_in_address": "0x4200000000000000000000000000000000000006", "token_out_address": "0x036CbD53842c5426634e7929541eC2318f3dCF7e", "amount_in": "0.1"}

The action handles: balance check, price quote, token approval, swap execution, and transaction monitoring."""


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
        user_address = wallet.default_address.address_id
        logger.info(user_address)
        # Input validation
        if float(amount_in) <= 0:
            return "Error: Input amount must be greater than 0"

        # Convert input amount to atomic units
        token_in = Asset.fetch(wallet.network_id, token_in_address)
        atomic_amount_in = int(token_in.to_atomic_amount(Decimal(amount_in)))
        logger.info(atomic_amount_in)

        # Check balance
        balance = 0
        for address in wallet.addresses:
            balance += address.balance(token_in_address)
            atomic_balance = int(token_in.to_atomic_amount(Decimal(balance)))

        if atomic_balance == 0:
            return f"Error: Insufficient balance. Have {atomic_balance}, need {atomic_amount_in}"

        if atomic_balance < atomic_amount_in:
            return f"Error: Insufficient balance. Have {atomic_balance}, need {atomic_amount_in}"

        # Approve Uniswap router if needed
        approval_result = approve(
            wallet, user_address, token_in_address, UNISWAP_ROUTER, atomic_amount_in
        )
        if approval_result.startswith("Error"):
            return f"Error approving Uniswap Router as spender: {approval_result}"

        # Get quote and calculate minimum output
        try:
            quote = get_uniswap_quote(
                token_in_address, token_out_address, atomic_amount_in
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
            "sqrtPriceLimitX96": 0,  # No price limit
        }

        # Estimate gas
        try:
            gas_estimate = wallet.estimate_gas(
                contract_address=UNISWAP_ROUTER,
                method="exactInputSingle",
                abi=UNISWAP_ROUTER_ABI,
                args=swap_args,
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
                args=swap_args,
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
