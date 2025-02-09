import os
import constants
import json

from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent

from cdp_langchain.agent_toolkits import CdpToolkit
from cdp_langchain.utils import CdpAgentkitWrapper

from db.wallet import add_wallet_info, get_wallet_info
from agent.custom_actions.get_latest_block import get_latest_block
from agent.handle_agent_action import execute_trade
from trading.uniswap_client import UniswapClient
from trading.operations import TradingOperations


def initialize_agent():
    """Initialize the agent with CDP Agentkit."""
    # Initialize LLM.
    llm = ChatOpenAI(model=constants.AGENT_MODEL)

    # Read wallet data from environment variable or database
    wallet_id = os.getenv(constants.WALLET_ID_ENV_VAR)
    wallet_seed = os.getenv(constants.WALLET_SEED_ENV_VAR)
    wallet_info = json.loads(get_wallet_info()) if get_wallet_info() else None

    # Configure CDP Agentkit Langchain Extension.
    values = {}

    # Load agent wallet information from database or environment variables
    if wallet_info:
        wallet_id = wallet_info["wallet_id"]
        wallet_seed = wallet_info["seed"]
        print(
            "Initialized CDP Agentkit with wallet data from database:",
            wallet_id,
            wallet_seed,
            flush=True,
        )
        values = {
            "cdp_wallet_data": json.dumps({"wallet_id": wallet_id, "seed": wallet_seed})
        }
    elif wallet_id and wallet_seed:
        print(
            "Initialized CDP Agentkit with wallet data from environment:",
            wallet_id,
            wallet_seed,
            flush=True,
        )
        values = {
            "cdp_wallet_data": json.dumps({"wallet_id": wallet_id, "seed": wallet_seed})
        }

    agentkit = CdpAgentkitWrapper(**values)

    # Export and store the updated wallet data back to environment variable
    wallet_data = agentkit.export_wallet()
    add_wallet_info(json.dumps(wallet_data))
    print("Exported wallet info", wallet_data, flush=True)

    # Initialize trading components
    uniswap_client = UniswapClient()
    trading_ops = TradingOperations()

    # Initialize CDP Agentkit Toolkit and get tools.
    cdp_toolkit = CdpToolkit.from_cdp_agentkit_wrapper(agentkit)
    base_tools = cdp_toolkit.get_tools()

    # Add custom trading tools
    trading_tools = [
        {
            "name": "execute_trade",
            "description": "Execute a trade between two tokens on Uniswap",
            "func": lambda token_in, token_out, amount_in, min_amount_out: execute_trade(
                uniswap_client,
                trading_ops,
                token_in,
                token_out,
                amount_in,
                min_amount_out,
                wallet_data["wallet_id"],
            ),
        },
        {
            "name": "get_token_price",
            "description": "Get the current price of a token in terms of ETH",
            "func": uniswap_client.get_token_price,
        },
        {
            "name": "check_arbitrage",
            "description": "Check for arbitrage opportunities in a token path",
            "func": uniswap_client.check_arbitrage_opportunity,
        },
        {
            "name": "estimate_gas",
            "description": "Estimate gas cost for a trade",
            "func": lambda token_in, token_out, amount_in: uniswap_client.estimate_gas(
                token_in, token_out, amount_in, wallet_data["wallet_id"]
            ),
        },
        get_latest_block,
    ]

    tools = base_tools + trading_tools

    # Store buffered conversation history in memory.
    memory = MemorySaver()

    # Create ReAct Agent using the LLM and CDP Agentkit tools.
    return create_react_agent(
        llm,
        tools=tools,
        checkpointer=memory,
        state_modifier=constants.AGENT_PROMPT,
    )
