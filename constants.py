from typing import Final

# Event types
EVENT_TYPE_AGENT: Final[str] = "agent"
EVENT_TYPE_COMPLETED: Final[str] = "completed"
EVENT_TYPE_TOOLS: Final[str] = "tools"
EVENT_TYPE_ERROR: Final[str]= "error"

# Environment variables
WALLET_ID_ENV_VAR: Final[str] = "CDP_WALLET_ID"
WALLET_SEED_ENV_VAR: Final[str] = "CDP_WALLET_SEED"

# Errors
class InputValidationError(Exception):
    """Custom exception for input validation errors"""
    pass

# Actions

TRADE_USDC_FOR_BTC: Final[str] = "trade_usdc_for_btc"
TRADE_USDC_FOR_ETH: Final[str] = "trade_usdc_for_eth"

# Agent
AGENT_MODEL: Final[str] = "gpt-4o-mini"
AGENT_PROMPT: Final[str] = """
You are a helpful agent that can interact onchain on the Base Layer 2 using the Coinbase Developer Platform Agentkit. 
You can execute trades between USDC and BTC/ETH. When trading:
1. Verify the user has sufficient balance
2. Confirm the trade details before execution
3. Provide trade confirmation
"""

# Add these to constants.py
UNISWAP_ROUTER_ADDRESS: Final[str] = "0x3fC91A3afd70395Cd496C647d5a6CC9D4B2b7FAD"  # Uniswap Router on Base Sepolia