"""
Base Agent
Parent class for all trading agents
"""

import os
import sys
from datetime import datetime
from pathlib import Path
import pandas as pd

class BaseAgent:
    def __init__(self, agent_type: str, instance_id: str = 'main'):
        """Initialize base agent with type and instance ID"""
        self.type = agent_type
        self.instance_id = instance_id
        self.start_time = datetime.now()
        self.active = True
        
    async def run(self):
        """Default run method - should be overridden by child classes"""
        raise NotImplementedError("Each agent must implement its own run method")
        
    def toggle_active(self):
        """Toggle agent active state"""
        self.active = not self.active
        return self.active   