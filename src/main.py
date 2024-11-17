import sys
import asyncio
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                           QLabel, QLineEdit, QPushButton, QTextEdit, QTabWidget,
                           QComboBox, QGridLayout)
from qasync import QEventLoop, asyncSlot
from monitor import TransactionMonitor
from datetime import datetime, timedelta

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.monitor = TransactionMonitor()
        self.is_monitoring = False
        self.initUI()

    def initUI(self):
        self.setWindowTitle('Solana Wallet Monitor')
        self.setGeometry(100, 100, 800, 600)

        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)

        tabs = QTabWidget()
        monitor_tab = self.create_monitor_tab()
        history_tab = self.create_history_tab()
        
        tabs.addTab(monitor_tab, "Live Feed")
        tabs.addTab(history_tab, "History")
        
        layout.addWidget(tabs)

    def create_monitor_tab(self):
        tab = QWidget()
        layout = QVBoxLayout()

        wallet_layout = QGridLayout()
        wallet_label = QLabel("Wallet Address:")
        self.wallet_input = QLineEdit()
        self.monitor_button = QPushButton("Start Monitoring")
        self.monitor_button.clicked.connect(self.toggle_monitoring)
        
        wallet_layout.addWidget(wallet_label, 0, 0)
        wallet_layout.addWidget(self.wallet_input, 0, 1)
        wallet_layout.addWidget(self.monitor_button, 0, 2)
        
        layout.addLayout(wallet_layout)

        self.transaction_display = QTextEdit()
        self.transaction_display.setReadOnly(True)
        layout.addWidget(self.transaction_display)

        self.monitor.set_callback(self.update_transaction_display)

        tab.setLayout(layout)
        return tab

    def create_history_tab(self):
        tab = QWidget()
        layout = QVBoxLayout()

        range_layout = QGridLayout()
        range_label = QLabel("Time Range:")
        self.range_selector = QComboBox()
        self.range_selector.addItems(["1 Day", "7 Days", "30 Days", "All Time"])
        self.update_history_button = QPushButton("Update")
        self.update_history_button.clicked.connect(self.update_history_display)
        
        range_layout.addWidget(range_label, 0, 0)
        range_layout.addWidget(self.range_selector, 0, 1)
        range_layout.addWidget(self.update_history_button, 0, 2)
        
        layout.addLayout(range_layout)

        self.history_display = QTextEdit()
        self.history_display.setReadOnly(True)
        layout.addWidget(self.history_display)

        tab.setLayout(layout)
        return tab

    def update_transaction_display(self, text):
        self.transaction_display.append(text)

    def update_history_display(self):
        range_text = self.range_selector.currentText()
        days = None
        if range_text == "1 Day":
            days = 1
        elif range_text == "7 Days":
            days = 7
        elif range_text == "30 Days":
            days = 30

        transactions = self.monitor.get_transaction_history(days)
        
        if not transactions:
            summary = "No transactions found for the selected period."
        else:
            total_transactions = len(transactions)
            summary = f"=== Transaction Summary (Last {range_text}) ===\n"
            summary += f"Total Transactions: {total_transactions}\n"
            summary += "\n=== Detailed Transactions ===\n"
            for tx in transactions:
                summary += f"\n{self.monitor.format_transaction_display(tx)}\n"
                summary += "-" * 50 + "\n"

        self.history_display.setText(summary)

    @asyncSlot()
    async def toggle_monitoring(self):
        if not self.is_monitoring:
            wallet = self.wallet_input.text().strip()
            if wallet:
                self.is_monitoring = True
                self.monitor_button.setText("Stop Monitoring")
                await self.monitor.start_monitoring(wallet)
        else:
            self.is_monitoring = False
            self.monitor_button.setText("Start Monitoring")
            await self.monitor.stop_monitoring()

def main():
    app = QApplication(sys.argv)
    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)
    
    window = MainWindow()
    window.show()
    
    with loop:
        loop.run_forever()

if __name__ == '__main__':
    main()