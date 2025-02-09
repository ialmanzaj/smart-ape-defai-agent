import constants
import re
from decimal import Decimal
import logging

from dotenv import load_dotenv
from agent.initialize_agent import AgentManager

load_dotenv()

logger = logging.getLogger(__name__)

agent_manager = AgentManager()
agentkit = agent_manager.agentkit


async def handle_agent_action(agent_action: str, content: str) -> None:
    """
    Handle various agent actions including trade execution and monitoring.
    """
    try:
        if agent_action == constants.TRADE_USDC_FOR_ETH:
            # Extract amount from content using regex
            amount_match = re.search(r"(\d+(\.\d+)?)", content)
            if not amount_match:
                raise ValueError("No valid amount found in content")
                
            amount = Decimal(amount_match.group(1))
            logger.info(f"Executing trade: {amount} USDC for ETH")
            
            try:
                # Execute the trade
                trade = await agentkit.execute_usdc_trade(
                    token_out_address=constants.ETH_ADDRESS,
                    amount_in=amount,
                    slippage_percentage=1.0
                )
                
                logger.info(f"Trade executed successfully: {trade}")
                
                # Monitor trade status
                status = await agentkit.get_trade_status(trade["transaction_hash"])
                logger.info(f"Trade status: {status}")
                
            except Exception as e:
                logger.error(f"Failed to execute trade: {str(e)}")
                raise
            
        elif agent_action == "check_trade_status":
            # Extract transaction hash from content
            tx_hash_match = re.search(r"0x[a-fA-F0-9]{64}", content)
            if tx_hash_match:
                tx_hash = tx_hash_match.group(0)
                status = await agentkit.get_trade_status(tx_hash)
                logger.info(f"Trade status for {tx_hash}: {status}")
            else:
                logger.error("No valid transaction hash found in content")

        elif agent_action == "monitor_price":
            # Extract token address from content
            token_address_match = re.search(r"0x[a-fA-F0-9]{40}", content)
            if token_address_match:
                token_address = token_address_match.group(0)
                price = await agentkit.get_token_price(token_address)
                logger.info(f"Price for token {token_address}: {price} USDC")
            else:
                logger.error("No valid token address found in content")

    except Exception as e:
        logger.error(f"Error handling agent action {agent_action}: {str(e)}")
        raise
