import constants
import re 


def handle_agent_action(agent_action, content):
    """
    Adds handling for the agent action.
    In our sample app, we just add deployed tokens and NFTs to the database.
    """
    if agent_action == constants.DEPLOY_TOKEN:
        # Search for contract address from output
        address = re.search(r'0x[a-fA-F0-9]{40}', content).group()
        # Add token to database
       
    if agent_action == constants.DEPLOY_NFT:
        # Search for contract address from output
        address = re.search(r'0x[a-fA-F0-9]{40}', content).group()
        # Add NFT to database
        