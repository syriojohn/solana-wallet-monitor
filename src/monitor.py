from datetime import datetime, timezone, timedelta
import json
from solders.signature import Signature
from solders.pubkey import Pubkey
from typing import Dict, Any
import asyncio
from solana.rpc.async_api import AsyncClient
from solana.rpc.commitment import Confirmed

class TransactionEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (Signature, Pubkey)):
            return str(obj)
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)

class TransactionHistory:
    def __init__(self, filename="transaction_history.json"):
        self.filename = filename
        self.transactions = []
        self.load_history()

    def load_history(self):
        try:
            with open(self.filename, 'r') as f:
                self.transactions = json.load(f)
        except FileNotFoundError:
            self.transactions = []
        except json.JSONDecodeError as e:
            print(f"Error loading history: {e}")
            self.transactions = []

    def save_history(self, new_transactions):
        try:
            self.transactions.extend(new_transactions)
            unique_transactions = {tx['signature']: tx for tx in self.transactions}.values()
            self.transactions = list(unique_transactions)
            
            with open(self.filename, 'w') as f:
                json.dump(self.transactions, f, cls=TransactionEncoder, indent=2)
        except Exception as e:
            print(f"Error saving history: {e}")

class TransactionMonitor:
    def __init__(self):
        self.history = TransactionHistory()
        self.client = AsyncClient("https://api.mainnet-beta.solana.com")
        self.monitoring = False
        self.current_wallet = None
        self.callback = None
        self.monitoring_task = None

    def set_callback(self, callback):
        self.callback = callback

    async def start_monitoring(self, wallet_address: str):
        try:
            pubkey = Pubkey.from_string(wallet_address)
            self.monitoring = True
            self.current_wallet = pubkey
            
            if self.monitoring_task:
                self.monitoring_task.cancel()
            
            self.monitoring_task = asyncio.create_task(self._monitor_wallet())
        except Exception as e:
            print(f"Error starting monitoring: {e}")
            if self.callback:
                self.callback(f"Error: Could not start monitoring - {str(e)}")

    async def stop_monitoring(self):
        self.monitoring = False
        if self.monitoring_task:
            self.monitoring_task.cancel()
            self.monitoring_task = None

    async def _monitor_wallet(self):
        try:
            while self.monitoring:
                print(f"Fetching transactions for wallet: {self.current_wallet}")
                response = await self.client.get_signatures_for_address(
                    self.current_wallet,
                    limit=20,
                    commitment=Confirmed
                )
                
                if response.value:
                    print(f"Found {len(response.value)} recent transactions")
                    new_transactions = []
                    
                    for tx_info in response.value:
                        tx_response = await self.client.get_transaction(
                            tx_info.signature,
                            commitment=Confirmed
                        )
                        
                        if tx_response.value:
                            parsed_tx = self.parse_transaction(tx_response.value, tx_response.value.block_time)
                            if parsed_tx:
                                new_transactions.append(parsed_tx)
                
                    if new_transactions:
                        self.history.save_history(new_transactions)
                        if self.callback:
                            for tx in new_transactions:
                                formatted_tx = self.format_transaction_display(tx)
                                self.callback(formatted_tx)
                
                await asyncio.sleep(2)
                
        except asyncio.CancelledError:
            print("Monitoring cancelled")
        except Exception as e:
            print(f"Error monitoring wallet: {e}")
            if self.callback:
                self.callback(f"Error: {str(e)}")

    def parse_transaction(self, tx_data, block_time):
        try:
            parsed_tx = {
                'signature': str(tx_data.transaction.signatures[0]),
                'timestamp': datetime.fromtimestamp(block_time, tz=timezone.utc).isoformat(),
                'token_transfers': [],
                'type': 'unknown'
            }

            if tx_data.meta:
                pre_balances = tx_data.meta.pre_balances
                post_balances = tx_data.meta.post_balances
                
                if len(pre_balances) > 0 and len(post_balances) > 0:
                    sol_transfer = (post_balances[0] - pre_balances[0]) / 1e9
                    if sol_transfer != 0:
                        parsed_tx['sol_transfer'] = sol_transfer
                        parsed_tx['type'] = 'sol_transfer'

                if tx_data.meta.pre_token_balances and tx_data.meta.post_token_balances:
                    for pre, post in zip(tx_data.meta.pre_token_balances, tx_data.meta.post_token_balances):
                        if pre and post and pre.owner == post.owner:
                            amount = (post.ui_token_amount.ui_amount or 0) - (pre.ui_token_amount.ui_amount or 0)
                            if amount != 0:
                                parsed_tx['token_transfers'].append({
                                    'amount': amount,
                                    'mint': str(pre.mint),
                                    'owner': str(pre.owner)
                                })
                                parsed_tx['type'] = 'token_transfer'

            return parsed_tx
        except Exception as e:
            print(f"Error parsing transaction: {e}")
            return None

    def format_transaction_display(self, transaction: Dict[str, Any]) -> str:
        try:
            timestamp = datetime.fromisoformat(transaction['timestamp'])
            formatted_time = timestamp.strftime('%Y-%m-%d %H:%M:%S')
            
            display = f"Time: {formatted_time}\n"
            display += f"Signature: {transaction['signature']}\n"
            display += f"Type: {transaction.get('type', 'Unknown')}\n"
            
            if 'token_transfers' in transaction:
                display += "Token Transfers:\n"
                for transfer in transaction['token_transfers']:
                    display += f"  Amount: {transfer['amount']} {transfer.get('symbol', 'Unknown')}\n"
            
            if 'sol_transfer' in transaction:
                display += f"SOL Transfer: {transaction['sol_transfer']} SOL\n"
                
            return display
        except Exception as e:
            return f"Error formatting transaction: {e}"

    async def close(self):
        await self.stop_monitoring()
        await self.client.close()

    def get_transaction_history(self, days=None):
        try:
            if not days:
                return self.history.transactions
            
            cutoff_time = datetime.now(timezone.utc) - timedelta(days=days)
            return [
                tx for tx in self.history.transactions 
                if datetime.fromisoformat(tx['timestamp']) > cutoff_time
            ]
        except Exception as e:
            print(f"Error getting transaction history: {e}")
            return []