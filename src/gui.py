import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import queue
from datetime import datetime
from models import TransactionHistory  # Changed from relative import

class WalletMonitorGUI:
    def __init__(self, history: TransactionHistory, update_queue: queue.Queue):
        self.root = tk.Tk()
        self.root.title("Solana Wallet Monitor")
        self.root.geometry("1000x800")
        
        self.history = history
        self.update_queue = update_queue
        self.wallet_address = tk.StringVar()
        self.monitoring_active = False
        self.start_callback = None
        self.stop_callback = None
        
        self._create_gui()
        
    def _create_gui(self):
        # Create main container
        main_container = ttk.Frame(self.root, padding="10")
        main_container.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Wallet Input Section
        self._create_wallet_section(main_container)
        
        # Create notebook for tabs
        notebook = ttk.Notebook(main_container)
        notebook.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=10)
        
        # Live Feed Tab
        self.live_feed = self._create_live_feed(notebook)
        notebook.add(self.live_feed, text="Live Feed")
        
        # Historical Summary Tab
        self.history_tab = self._create_history_tab(notebook)
        notebook.add(self.history_tab, text="Historical Summary")
        
        # Configure grid weights
        main_container.columnconfigure(0, weight=1)
        main_container.rowconfigure(1, weight=1)
        
    def _create_wallet_section(self, parent):
        wallet_frame = ttk.LabelFrame(parent, text="Wallet Configuration", padding="5")
        wallet_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # Wallet address input
        ttk.Label(wallet_frame, text="Wallet Address:").grid(row=0, column=0, padx=5)
        address_entry = ttk.Entry(wallet_frame, textvariable=self.wallet_address, width=50)
        address_entry.grid(row=0, column=1, padx=5)
        
        # Control buttons
        self.start_button = ttk.Button(wallet_frame, text="Start Monitoring", command=self._toggle_monitoring)
        self.start_button.grid(row=0, column=2, padx=5)
        
        wallet_frame.columnconfigure(1, weight=1)
        
    def _create_live_feed(self, parent):
        frame = ttk.Frame(parent)
        
        # Create text widget for live transactions
        self.live_text = scrolledtext.ScrolledText(frame, height=20, width=100)
        self.live_text.pack(expand=True, fill='both', padx=5, pady=5)
        
        return frame
        
    def _create_history_tab(self, parent):
        frame = ttk.Frame(parent)
        
        # Period selector
        period_frame = ttk.Frame(frame)
        period_frame.pack(fill='x', padx=5, pady=5)
        
        ttk.Label(period_frame, text="Summary Period:").pack(side=tk.LEFT)
        self.period_var = tk.StringVar(value="7")
        period_combo = ttk.Combobox(period_frame, textvariable=self.period_var, 
                                  values=["1", "7", "30", "90"], width=5)
        period_combo.pack(side=tk.LEFT, padx=5)
        ttk.Label(period_frame, text="days").pack(side=tk.LEFT)
        
        # Summary text widget
        self.summary_text = scrolledtext.ScrolledText(frame, height=20, width=100)
        self.summary_text.pack(expand=True, fill='both', padx=5, pady=5)
        
        # Bind period change
        self.period_var.trace('w', self.update_summary)
        
        return frame
    
    def _toggle_monitoring(self):
        if not self.monitoring_active:
            if not self.wallet_address.get().strip():
                messagebox.showerror("Error", "Please enter a wallet address")
                return
                
            self.monitoring_active = True
            self.start_button.config(text="Stop Monitoring")
            if self.start_callback:
                self.start_callback(self.wallet_address.get())
        else:
            self.monitoring_active = False
            self.start_button.config(text="Start Monitoring")
            if self.stop_callback:
                self.stop_callback()
    
    def add_live_transaction(self, tx_info: str):
        """Add a new transaction to the live feed."""
        self.live_text.insert('1.0', f"\n{tx_info}\n{'='*60}\n")
        self.live_text.see('1.0')
    
    def update_summary(self, *args):
        """Update the historical summary display."""
        try:
            days = int(self.period_var.get())
            summary = self.history.get_summary(days)
            
            text = f"=== Transaction Summary (Last {days} Days) ===\n\n"
            text += f"Total Transactions: {summary['total_transactions']}\n"
            text += f"Total Volume (USD): ${summary['total_volume_usd']:,.2f}\n\n"
            
            text += "=== Token Activity ===\n"
            for token, data in summary['tokens'].items():
                text += f"\n{token}:\n"
                text += f"  Total Received: {data['total_in']:,.4f}\n"
                text += f"  Total Sent: {data['total_out']:,.4f}\n"
                text += f"  Volume (USD): ${data['volume_usd']:,.2f}\n"
            
            text += "\n=== Transaction Types ===\n"
            for tx_type, count in summary['transaction_types'].items():
                text += f"{tx_type}: {count}\n"
            
            self.summary_text.delete('1.0', tk.END)
            self.summary_text.insert('1.0', text)
            
        except Exception as e:
            print(f"Error updating summary: {e}")
    
    def set_callbacks(self, start_callback, stop_callback):
        """Set callbacks for start/stop monitoring."""
        self.start_callback = start_callback
        self.stop_callback = stop_callback
    
    def start(self):
        """Start the GUI main loop."""
        self.update_check()
        self.root.mainloop()
    
    def update_check(self):
        """Check for updates from the monitor thread."""
        try:
            while not self.update_queue.empty():
                _ = self.update_queue.get_nowait()
                self.update_summary()
        except queue.Empty:
            pass
        finally:
            self.root.after(1000, self.update_check)