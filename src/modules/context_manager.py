"""
Context Manager Module
Handles conversation context and trading session management
"""

from typing import Dict, List, Optional
from datetime import datetime, timedelta
from termcolor import cprint

class ContextManager:
    def __init__(self):
        self.contexts: Dict[str, Dict] = {}  # session_id -> context
        self.session_timeout = timedelta(minutes=30)
        
    def create_session(self, session_id: str) -> Dict:
        """Create a new conversation session"""
        self.contexts[session_id] = {
            "created_at": datetime.now(),
            "last_updated": datetime.now(),
            "language": "en",  # Default to English
            "conversation_history": [],
            "trading_context": {
                "active_tokens": set(),
                "pending_trades": [],
                "risk_preferences": {
                    "max_slippage": 2.5,  # Default 2.5%
                    "min_liquidity": 0.5   # Default 0.5 liquidity score
                }
            }
        }
        return self.contexts[session_id]
        
    def get_session(self, session_id: str) -> Optional[Dict]:
        """Get existing session or None if expired"""
        if session_id not in self.contexts:
            return None
            
        session = self.contexts[session_id]
        if datetime.now() - session["last_updated"] > self.session_timeout:
            del self.contexts[session_id]
            return None
            
        return session
        
    def update_session(self, session_id: str, message: Dict) -> None:
        """Update session with new message"""
        session = self.get_session(session_id)
        if not session:
            session = self.create_session(session_id)
            
        # Update session
        session["last_updated"] = datetime.now()
        session["conversation_history"].append({
            "timestamp": datetime.now().isoformat(),
            "message": message
        })
        
        # Detect language if not set
        if "language" not in message and len(session["conversation_history"]) == 1:
            session["language"] = self._detect_language(message.get("content", ""))
            
    def get_conversation_history(self, session_id: str, limit: int = 10) -> List[Dict]:
        """Get recent conversation history"""
        session = self.get_session(session_id)
        if not session:
            return []
            
        history = session["conversation_history"]
        return history[-limit:] if limit > 0 else history
        
    def get_trading_context(self, session_id: str) -> Dict:
        """Get trading context for session"""
        session = self.get_session(session_id)
        if not session:
            return {}
            
        return session["trading_context"]
        
    def update_trading_context(self, session_id: str, updates: Dict) -> None:
        """Update trading context with new data"""
        session = self.get_session(session_id)
        if not session:
            session = self.create_session(session_id)
            
        trading_context = session["trading_context"]
        
        # Update active tokens
        if "active_tokens" in updates:
            trading_context["active_tokens"].update(updates["active_tokens"])
            
        # Update pending trades
        if "pending_trades" in updates:
            trading_context["pending_trades"].extend(updates["pending_trades"])
            # Clean up completed trades
            trading_context["pending_trades"] = [
                trade for trade in trading_context["pending_trades"]
                if trade.get("status") == "pending"
            ]
            
        # Update risk preferences
        if "risk_preferences" in updates:
            trading_context["risk_preferences"].update(updates["risk_preferences"])
            
    def _detect_language(self, text: str) -> str:
        """Detect message language (en/zh)"""
        # Simple detection based on character ranges
        chinese_chars = len([c for c in text if '\u4e00' <= c <= '\u9fff'])
        return "zh" if chinese_chars > len(text) * 0.5 else "en"
        
    def cleanup_expired_sessions(self) -> None:
        """Remove expired sessions"""
        current_time = datetime.now()
        expired = [
            session_id for session_id, session in self.contexts.items()
            if current_time - session["last_updated"] > self.session_timeout
        ]
        for session_id in expired:
            del self.contexts[session_id]
