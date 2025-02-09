from typing import AsyncIterator
import os
import logging
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage
import constants
from utils import format_sse
from agent.initialize_agent import initialize_agent
from agent.handle_agent_action import handle_agent_action

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def run_agent(input, agent_executor, config) -> AsyncIterator[str]:
    """Run the agent and yield formatted SSE messages"""
    try:
        async for chunk in agent_executor.astream(
            {"messages": [HumanMessage(content=input)]}, config
        ):
            if "agent" in chunk:
                content = chunk["agent"]["messages"][0].content
                if content:
                    yield format_sse(content, constants.EVENT_TYPE_AGENT)
                    logger.info(f"Agent message: {content}")
            elif "tools" in chunk:
                name = chunk["tools"]["messages"][0].name
                content = chunk["tools"]["messages"][0].content
                if content:
                    yield format_sse(content, constants.EVENT_TYPE_TOOLS, functions=[name])
                    logger.info(f"Tool execution: {name} - {content}")
                    await handle_agent_action(name, content)
    except Exception as e:
        error_msg = f"Error: {str(e)}"
        logger.error(error_msg)
        yield format_sse(error_msg, constants.EVENT_TYPE_ERROR)