from decimal import Decimal
from typing import Optional, Dict, Union
import os
from dotenv import load_dotenv
from cdp import Cdp, Wallet


class TradingCore:
    def __init__(self, network: str = "base-sepolia"):
        """
        Initialize TradingCore with CDP SDK
        
        Args:
            network: The network to use (default: base-sepolia)
        """
        # Load environment variables
        load_dotenv()
        
        # Configure CDP SDK
        api_key_name = os.getenv('CDP_API_KEY_NAME')
        api_key_private_key = os.getenv('CDP_API_KEY_PRIVATE_KEY')
        
        if not api_key_name or not api_key_private_key:
            raise ValueError("CDP API credentials not found in environment variables")
        
        # Initialize CDP SDK
        Cdp.configure(api_key_name, api_key_private_key)
        
        # Store network
        self.network = network
        
    def create_wallet(self) -> Dict[str, str]:
        """
        Create a new wallet
        
        Returns:
            Dict containing wallet information
        """
        try:
            wallet = Wallet.create(self.network)
            return {
                'wallet_id': wallet.id,
                'address': wallet.default_address.address_id,
                'network': self.network
            }
        except Exception as e:
            raise Exception(f"Failed to create wallet: {str(e)}")

    def get_balance(self, wallet_id: str, asset_id: str = 'eth') -> Decimal:
        """
        Get balance for a specific asset
        
        Args:
            wallet_id: The wallet ID to check
            asset_id: Asset identifier (default: eth)
        """
        try:
            wallet = Wallet.fetch(wallet_id)
            # Note: This is a simplified approach - you'd need to implement
            # actual balance checking based on the CDP SDK's capabilities
            balances = wallet.default_address.balances()
            return Decimal(str(next((b for b in balances if b.asset.id.lower() == asset_id.lower()), 0)))
        except Exception as e:
            raise Exception(f"Failed to get balance: {str(e)}")

    def create_trade(
        self,
        wallet_id: str,
        amount: Decimal,
        from_asset: str,
        to_asset: str
    ) -> Dict[str, Union[str, Decimal]]:
        """
        Create a trade order using CDP SDK
        
        Args:
            wallet_id: The wallet ID to trade from
            amount: Amount to trade
            from_asset: Asset to trade from
            to_asset: Asset to trade to
        """
        try:
            wallet = Wallet.fetch(wallet_id)
            
            # Execute trade
            trade = wallet.trade(
                float(amount),  # CDP SDK expects float
                from_asset.lower(),
                to_asset.lower()
            ).wait()
            
            return {
                'transaction_id': trade.id,
                'status': trade.status,
                'from_asset': from_asset,
                'to_asset': to_asset,
                'amount': amount
            }
        except Exception as e:
            raise Exception(f"Failed to create trade: {str(e)}")

    def transfer(
        self,
        from_wallet_id: str,
        to_address: str,
        amount: Decimal,
        asset: str = 'eth',
        gasless: bool = False
    ) -> Dict[str, str]:
        """
        Transfer assets using CDP SDK
        
        Args:
            from_wallet_id: Source wallet ID
            to_address: Destination address
            amount: Amount to transfer
            asset: Asset to transfer (default: eth)
            gasless: Whether to use gasless transfer (default: False)
        """
        try:
            wallet = Wallet.fetch(from_wallet_id)
            
            # Execute transfer
            transfer = wallet.transfer(
                float(amount),  # CDP SDK expects float
                asset.lower(),
                to_address,
                gasless=gasless
            ).wait()
            
            return {
                'transaction_id': transfer.id,
                'status': transfer.status,
                'network': self.network
            }
        except Exception as e:
            raise Exception(f"Failed to process transfer: {str(e)}")


# Usage example:
def main():
    try:
        # Initialize trading core with Base mainnet
        trading = TradingCore("base-mainnet")
        
        # Create a new wallet
        wallet_info = trading.create_wallet()
        print(f"Created wallet: {wallet_info}")
        
        # Check balance
        balance = trading.get_balance(wallet_info['wallet_id'])
        print(f"Current ETH balance: {balance}")
        
        # Create a trade
        trade = trading.create_trade(
            wallet_id=wallet_info['wallet_id'],
            amount=Decimal("0.1"),
            from_asset="ETH",
            to_asset="USDC"
        )
        print(f"Trade executed: {trade}")
        
        # Set up webhook for monitoring
        webhook = trading.setup_webhook(
            wallet_id=wallet_info['wallet_id'],
            notification_url="https://your-app.com/callback",
            event_type="ERC20_TRANSFER"
        )
        print(f"Webhook configured: {webhook}")
        
    except Exception as e:
        print(f"Error: {str(e)}")