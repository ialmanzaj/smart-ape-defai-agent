import os
import constants
import json
from typing import Optional

from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent

from cdp_langchain.agent_toolkits import CdpToolkit
from cdp_langchain.utils import CdpAgentkitWrapper

from db.wallet import add_wallet_info, get_wallet_info
from agent.custom_actions.get_latest_block import get_latest_block

class AgentManager:
    _instance: Optional['AgentManager'] = None
    _agent = None
    _cdp_toolkit = None
    _agentkit = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(AgentManager, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not self._agent:
            self._initialize()

    def _initialize(self):
        """Initialize the agent and CDP toolkit."""
        # Initialize LLM
        llm = ChatOpenAI(model=constants.AGENT_MODEL)

        # Initialize CDP Agentkit with wallet data
        self._agentkit = self._setup_agentkit()
        
        # Initialize CDP toolkit
        self._cdp_toolkit = CdpToolkit.from_cdp_agentkit_wrapper(self._agentkit)
        tools = self._cdp_toolkit.get_tools() + [get_latest_block]

        # Create ReAct Agent
        memory = MemorySaver()
        self._agent = create_react_agent(
            llm,
            tools=tools,
            checkpointer=memory,
            state_modifier=constants.AGENT_PROMPT,
        )

    def _setup_agentkit(self) -> CdpAgentkitWrapper:
        """Set up CDP Agentkit with wallet configuration."""
        wallet_id = os.getenv(constants.WALLET_ID_ENV_VAR)
        wallet_seed = os.getenv(constants.WALLET_SEED_ENV_VAR)
        wallet_info = json.loads(get_wallet_info()) if get_wallet_info() else None

        values = {}
        if wallet_info:
            wallet_id = wallet_info["wallet_id"]
            wallet_seed = wallet_info["seed"]
            print("Using wallet data from database:", wallet_id, flush=True)
            values = {"cdp_wallet_data": json.dumps({"wallet_id": wallet_id, "seed": wallet_seed})}
        elif wallet_id and wallet_seed:
            print("Using wallet data from environment:", wallet_id, flush=True)
            values = {"cdp_wallet_data": json.dumps({"wallet_id": wallet_id, "seed": wallet_seed})}

        agentkit = CdpAgentkitWrapper(**values)
        
        
        
        # Store updated wallet data
        wallet_data = agentkit.export_wallet()
        add_wallet_info(json.dumps(wallet_data))
        print("Exported wallet info to database", flush=True)
        
        return agentkit

    @property
    def agent(self):
        """Get the initialized agent."""
        return self._agent

    @property
    def cdp_toolkit(self):
        """Get the initialized CDP toolkit."""
        return self._cdp_toolkit

    @property
    def agentkit(self):
        """Get the initialized CDP agentkit."""
        return self._agentkit

def get_agent_manager() -> AgentManager:
    """Get the singleton instance of AgentManager."""
    return AgentManager()

# For backward compatibility
def initialize_agent():
    """Legacy function to get the initialized agent."""
    return get_agent_manager().agent