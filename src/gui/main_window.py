import sys
import json
import logging
from datetime import datetime
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                           QTextEdit, QPushButton, QLabel, QLineEdit)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from qt_material import apply_stylesheet

# Configure logging
logging.basicConfig(
    filename='user_operations.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class TradeWorker(QThread):
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)
    
    def __init__(self, trade_instruction):
        super().__init__()
        self.trade_instruction = trade_instruction
        
    def run(self):
        try:
            # Execute trade logic here
            from src.data.jupiter_client_v2 import JupiterClientV2
            client = JupiterClientV2()
            # Log the trade attempt
            logging.info(f"Trade instruction received: {self.trade_instruction}")
            self.finished.emit({"status": "pending", "message": "交易执行中..."})
        except Exception as e:
            logging.error(f"Trade execution error: {str(e)}")
            self.error.emit(str(e))

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Solana 交易系统 | Solana Trading System")
        self.setMinimumSize(800, 600)
        
        # Create main widget and layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)
        
        # Add input area
        self.input_label = QLabel("输入交易指令 | Enter Trading Instruction:")
        layout.addWidget(self.input_label)
        
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("例如: 买入500个AI16z代币，滑点不超过2%")
        layout.addWidget(self.input_field)
        
        # Add execute button
        self.execute_button = QPushButton("执行交易 | Execute Trade")
        self.execute_button.clicked.connect(self.execute_trade)
        layout.addWidget(self.execute_button)
        
        # Add output area
        self.output_label = QLabel("交易状态 | Trade Status:")
        layout.addWidget(self.output_label)
        
        self.output_area = QTextEdit()
        self.output_area.setReadOnly(True)
        layout.addWidget(self.output_area)
        
        # Apply material theme
        apply_stylesheet(self, theme='dark_teal.xml')
        
        # Log application start
        logging.info("GUI application started")
        
    def execute_trade(self):
        instruction = self.input_field.text()
        if not instruction:
            self.output_area.append("❌ 请输入交易指令 | Please enter trading instruction")
            logging.warning("Empty trade instruction attempted")
            return
            
        # Log the trade instruction
        logging.info(f"User initiated trade: {instruction}")
        
        # Create worker thread for trade execution
        self.worker = TradeWorker(instruction)
        self.worker.finished.connect(self.handle_trade_result)
        self.worker.error.connect(self.handle_trade_error)
        self.worker.start()
        
        self.output_area.append(f"\n🔄 执行中 | Executing: {instruction}")
        self.execute_button.setEnabled(False)
        
    def handle_trade_result(self, result):
        self.output_area.append(f"\n✅ {result['message']}")
        self.execute_button.setEnabled(True)
        logging.info(f"Trade completed: {result}")
        
    def handle_trade_error(self, error):
        self.output_area.append(f"\n❌ 错误 | Error: {error}")
        self.execute_button.setEnabled(True)
        logging.error(f"Trade error: {error}")

def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
