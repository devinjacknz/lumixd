"""
Tests for GUI Chat Window Module
"""

import pytest
from unittest.mock import MagicMock, patch
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from src.modules.gui_chat import ChatWindow

@pytest.fixture
def app():
    """Create QApplication instance"""
    return QApplication([])

@pytest.fixture
def chat_window(app):
    """Create ChatWindow instance"""
    window = ChatWindow()
    return window

def test_window_initialization(chat_window):
    """Test window initialization"""
    assert chat_window.windowTitle() == "Lumix Trading System"
    assert chat_window.size().width() == 1200
    assert chat_window.size().height() == 800
    assert chat_window.chat_history is not None
    assert chat_window.message_input is not None
    assert chat_window.send_button is not None

def test_send_message(chat_window):
    """Test message sending"""
    # Mock message_sent signal
    signal_mock = MagicMock()
    chat_window.message_sent.connect(signal_mock)
    
    # Set message and send
    test_message = "Test message"
    chat_window.message_input.setText(test_message)
    chat_window.send_message()
    
    # Verify signal emission
    signal_mock.assert_called_once_with(test_message)
    # Verify input cleared
    assert chat_window.message_input.text() == ""
    # Verify message in chat history
    assert test_message in chat_window.chat_history.toPlainText()

def test_receive_message(chat_window):
    """Test message receiving"""
    test_message = "Test response"
    chat_window.receive_message(test_message, "System")
    assert test_message in chat_window.chat_history.toPlainText()
    assert "System" in chat_window.chat_history.toPlainText()

def test_update_trading_status(chat_window):
    """Test trading status updates"""
    status = {
        "active": True,
        "last_update": "2024-02-10 12:00:00",
        "success_rate": 95,
        "volume_24h": 1000
    }
    chat_window.update_trading_status(status)
    status_text = chat_window.status_info.text()
    assert "Active: True" in status_text
    assert "Success Rate: 95%" in status_text
    assert "Volume: 1000" in status_text

@patch('darkdetect.isDark')
def test_theme_switching(mock_is_dark, chat_window):
    """Test theme switching"""
    # Test light theme
    mock_is_dark.return_value = False
    chat_window.theme_selector.setCurrentText("Light")
    chat_window.change_theme("Light")
    
    # Test dark theme
    mock_is_dark.return_value = True
    chat_window.theme_selector.setCurrentText("Dark")
    chat_window.change_theme("Dark")
    
    # Test system theme
    chat_window.theme_selector.setCurrentText("System")
    chat_window.change_theme("System")
    chat_window.check_system_theme()

def test_error_handling(chat_window):
    """Test error handling in status updates"""
    chat_window.update_trading_status({"invalid": "data"})
    assert "Error updating status" in chat_window.status_info.text()

def test_chart_placeholder(chat_window):
    """Test chart widget initialization"""
    assert chat_window.chart_widget is not None
    assert chat_window.chart_widget.minimumHeight() == 300
