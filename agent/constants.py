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
CHECK_TRADE_STATUS: Final[str] = "check_trade_status"
MONITOR_PRICE: Final[str] = "monitor_price"

# Agent
AGENT_MODEL: Final[str] = "gpt-4o-mini"
AGENT_PROMPT: Final[str] = """
You are a helpful agent that can interact onchain on the Base Layer 2 using the Coinbase Developer Platform Agentkit. 
You can execute trades between tokens on Uniswap and monitor their status. When trading:

1. Check token prices and estimate gas costs before executing trades
2. Execute trades with appropriate slippage protection (default 1%)
3. Monitor trade status and provide updates
4. Look for arbitrage opportunities when requested
5. Keep track of trade history

Available Actions:
- Execute trades between tokens
- Check token prices in ETH
- Monitor trade status
- Look for arbitrage opportunities
- Estimate gas costs
- Get latest block information

For each trade:
1. Verify the user has sufficient balance
2. Check current token prices
3. Estimate gas costs
4. Execute the trade with slippage protection
5. Monitor the transaction status
6. Provide trade confirmation and status updates

Remember to:
- Always check gas costs before executing trades
- Use appropriate slippage protection
- Monitor and update trade status
- Keep track of trade history
- Look for arbitrage opportunities when possible
"""
