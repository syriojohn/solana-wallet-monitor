import requests
from typing import Optional, Dict, List
from solana.rpc.api import Client
from models import TokenMetadata  # Regular import, not relative

class PriceTracker:
    def __init__(self):
        self.prices: Dict[str, float] = {}
        self.coingecko_base_url = "https://api.coingecko.com/api/v3"
        
    def update_prices(self, token_ids: List[str]):
        """Update prices for multiple tokens at once."""
        if not token_ids:
            return
            
        try:
            ids_string = ",".join(token_ids)
            response = requests.get(
                f"{self.coingecko_base_url}/simple/price",
                params={
                    "ids": ids_string,
                    "vs_currencies": "usd"
                }
            )
            if response.status_code == 200:
                data = response.json()
                for token_id in token_ids:
                    if token_id in data:
                        self.prices[token_id] = data[token_id]["usd"]
        except Exception as e:
            print(f"Error updating prices: {e}")
    
    def get_price(self, token_id: str) -> Optional[float]:
        return self.prices.get(token_id)

class TokenRegistry:
    def __init__(self):
        self.client = Client("https://api.mainnet-beta.solana.com")
        self.tokens: Dict[str, TokenMetadata] = {}
        self.load_token_list()
        
    def load_token_list(self):
        """Load token list from Jupiter API."""
        try:
            response = requests.get("https://token.jup.ag/all")
            if response.status_code == 200:
                tokens = response.json()
                for token in tokens:
                    self.tokens[token['address']] = TokenMetadata(
                        address=token['address'],
                        name=token.get('name', ''),
                        symbol=token.get('symbol', ''),
                        decimals=token.get('decimals', 9),
                        coingecko_id=token.get('coingeckoId', '')
                    )
        except Exception as e:
            print(f"Error loading token list: {e}")

    def get_token_info(self, mint_address: str) -> TokenMetadata:
        return self.tokens.get(mint_address, TokenMetadata(address=mint_address))