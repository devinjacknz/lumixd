"""
GUI Chat Window Module
Provides modern UI interface for trading system interaction
"""

from typing import Dict, Optional, List
import json
from datetime import datetime
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QTextEdit, QLineEdit, QPushButton, QLabel,
    QComboBox, QFrame, QScrollArea, QSplitter
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QPalette, QColor
from qt_material import apply_stylesheet
import darkdetect
from src.config.settings import TRADING_CONFIG

class ChatWindow(QMainWindow):
    message_sent = pyqtSignal(str)  # Signal for sending messages
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Lumix Trading System")
        self.resize(1200, 800)
        
        # Initialize UI components
        self.init_ui()
        
        # Setup theme
        self.setup_theme()
        
        # Setup auto theme detection
        if TRADING_CONFIG.get("gui_config", {}).get("theme_auto", True):
            self.theme_timer = QTimer()
            self.theme_timer.timeout.connect(self.check_system_theme)
            self.theme_timer.start(5000)  # Check every 5 seconds
            
    def init_ui(self):
        """Initialize the UI components"""
        # Create central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        
        # Create left panel (chat)
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        
        # Chat history
        self.chat_history = QTextEdit()
        self.chat_history.setReadOnly(True)
        left_layout.addWidget(self.chat_history)
        
        # Input area
        input_widget = QWidget()
        input_layout = QHBoxLayout(input_widget)
        
        self.message_input = QLineEdit()
        self.message_input.returnPressed.connect(self.send_message)
        self.send_button = QPushButton("Send")
        self.send_button.clicked.connect(self.send_message)
        
        input_layout.addWidget(self.message_input)
        input_layout.addWidget(self.send_button)
        left_layout.addWidget(input_widget)
        
        # Create right panel (trading info)
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        
        # Trading status
        status_frame = QFrame()
        status_frame.setFrameStyle(QFrame.Shape.StyledPanel)
        status_layout = QVBoxLayout(status_frame)
        
        self.status_label = QLabel("Trading Status")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        status_layout.addWidget(self.status_label)
        
        self.status_info = QLabel("Initializing...")
        status_layout.addWidget(self.status_info)
        
        right_layout.addWidget(status_frame)
        
        # K-line chart placeholder
        chart_frame = QFrame()
        chart_frame.setFrameStyle(QFrame.Shape.StyledPanel)
        chart_layout = QVBoxLayout(chart_frame)
        
        chart_label = QLabel("K-Line Chart")
        chart_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        chart_layout.addWidget(chart_label)
        
        self.chart_widget = QWidget()
        self.chart_widget.setMinimumHeight(300)
        chart_layout.addWidget(self.chart_widget)
        
        right_layout.addWidget(chart_frame)
        
        # Theme selector
        theme_widget = QWidget()
        theme_layout = QHBoxLayout(theme_widget)
        
        theme_label = QLabel("Theme:")
        self.theme_selector = QComboBox()
        self.theme_selector.addItems(["Light", "Dark", "System"])
        self.theme_selector.currentTextChanged.connect(self.change_theme)
        
        theme_layout.addWidget(theme_label)
        theme_layout.addWidget(self.theme_selector)
        right_layout.addWidget(theme_widget)
        
        # Add panels to main layout with splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setStretchFactor(0, 2)  # Left panel takes 2/3 of width
        splitter.setStretchFactor(1, 1)  # Right panel takes 1/3 of width
        
        main_layout.addWidget(splitter)
        
    def setup_theme(self):
        """Setup initial theme"""
        system_theme = "dark" if darkdetect.isDark() else "light"
        apply_stylesheet(self, theme=f"{system_theme}_blue.xml")
        
    def check_system_theme(self):
        """Check and update theme based on system settings"""
        if self.theme_selector.currentText() == "System":
            self.setup_theme()
            
    def change_theme(self, theme: str):
        """Change application theme"""
        if theme == "System":
            self.setup_theme()
        else:
            apply_stylesheet(self, theme=f"{theme.lower()}_blue.xml")
            
    def send_message(self):
        """Send a message"""
        message = self.message_input.text().strip()
        if message:
            # Add message to chat history
            timestamp = datetime.now().strftime("%H:%M:%S")
            self.chat_history.append(f"<b>You ({timestamp}):</b> {message}")
            
            # Clear input
            self.message_input.clear()
            
            # Emit message signal
            self.message_sent.emit(message)
            
    def receive_message(self, message: str, source: str = "System"):
        """Receive and display a message"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.chat_history.append(f"<b>{source} ({timestamp}):</b> {message}")
        
    def update_trading_status(self, status: Dict):
        """Update trading status display"""
        try:
            status_text = f"""
            <b>Trading Status:</b><br>
            Active: {status.get('active', False)}<br>
            Last Update: {status.get('last_update', 'Never')}<br>
            Success Rate: {status.get('success_rate', '0')}%<br>
            24h Volume: {status.get('volume_24h', '0')} SOL
            """
            self.status_info.setText(status_text)
        except Exception as e:
            self.status_info.setText(f"Error updating status: {str(e)}")
            
    def update_chart(self, data: Dict):
        """Update K-line chart with new data"""
        # TODO: Implement chart update using a proper charting library
        pass
