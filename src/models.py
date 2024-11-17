from dataclasses import dataclass
from typing import Optional, Dict, List
from datetime import datetime, timedelta
import json
from pathlib import Path

@dataclass
class TokenMetadata:
    address: str
    name: str = ""
    symbol: str = ""
    decimals: int = 9
    coingecko_id: str = ""

class TransactionHistory:
    def __init__(self):
        self.transactions: List[Dict] = []
        self.history_file = Path("solana_transaction_history.json")
        self.load_history()
        
    def load_history(self):
        if self.history_file.exists():
            try:
                with open(self.history_file, 'r') as f:
                    self.transactions = json.load(f)
            except Exception as e:
                print(f"Error loading history: {e}")
                
    def save_history(self):
        try:
            with open(self.history_file, 'w') as f:
                json.dump(self.transactions, f, indent=2)
        except Exception as e:
            print(f"Error saving history: {e}")
            
    def add_transaction(self, tx_info: Dict):
        self.transactions.append(tx_info)
        self.save_history()
        
    def get_summary(self, days: int = 7) -> Dict:
        cutoff = datetime.now() - timedelta(days=days)
        recent_txs = [tx for tx in self.transactions 
                     if datetime.strptime(tx['timestamp'], '%Y-%m-%d %H:%M:%S') > cutoff]
        
        summary = {
            'total_transactions': len(recent_txs),
            'total_volume_usd': sum(tx.get('total_value_usd', 0) for tx in recent_txs),
            'tokens': {},
            'transaction_types': {}
        }
        
        for tx in recent_txs:
            # Aggregate token volumes
            for action in tx['actions']:
                token_symbol = action.get('token_symbol', 'Unknown')
                if token_symbol not in summary['tokens']:
                    summary['tokens'][token_symbol] = {
                        'total_in': 0,
                        'total_out': 0,
                        'volume_usd': 0
                    }
                
                if action['type'] == 'received':
                    summary['tokens'][token_symbol]['total_in'] += float(action['amount_change'])
                else:
                    summary['tokens'][token_symbol]['total_out'] += float(action['amount_change'])
                    
                summary['tokens'][token_symbol]['volume_usd'] += float(action.get('value_usd', 0))
            
            # Aggregate transaction types
            tx_type = tx.get('transaction_type', 'Unknown')
            summary['transaction_types'][tx_type] = summary['transaction_types'].get(tx_type, 0) + 1
            
        return summary