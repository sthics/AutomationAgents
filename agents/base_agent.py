#!/usr/bin/env python3
"""
Base Agent Class
Common functionality for all AI agents
"""

import os
import json
import logging
import requests
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from dotenv import load_dotenv

load_dotenv()

class BaseAgent(ABC):
    """Base class for all AI agents"""
    
    def __init__(self, name: str):
        self.name = name
        self.logger = self._setup_logger()
        self.ollama_url = os.getenv('OLLAMA_HOST', 'http://localhost:11434')
        self.default_model = os.getenv('DEFAULT_MODEL', 'llama2')
        
    def _setup_logger(self) -> logging.Logger:
        """Setup logger for the agent"""
        logger = logging.getLogger(f"{self.name}_agent")
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                f'%(asctime)s - {self.name.upper()} - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
    
    def ask_ai(self, prompt: str, model: Optional[str] = None) -> str:
        """Send prompt to local AI model"""
        model = model or self.default_model
        
        try:
            data = {
                "model": model,
                "prompt": prompt,
                "stream": False
            }
            
            response = requests.post(f"{self.ollama_url}/api/generate", json=data)
            
            if response.status_code == 200:
                return response.json()['response']
            else:
                error_msg = f"AI request failed with status {response.status_code}"
                self.logger.error(error_msg)
                return error_msg
                
        except Exception as e:
            error_msg = f"AI Error: {e}"
            self.logger.error(error_msg)
            return error_msg
    
    def test_connection(self) -> bool:
        """Test if the agent can connect to its service"""
        try:
            return self._test_service_connection()
        except Exception as e:
            self.logger.error(f"Connection test failed: {e}")
            return False
    
    @abstractmethod
    def _test_service_connection(self) -> bool:
        """Test connection to the specific service (implement in subclass)"""
        pass
    
    @abstractmethod
    def get_status(self) -> Dict[str, Any]:
        """Get current status of the agent"""
        pass
    
    def log_action(self, action: str, details: str = ""):
        """Log an action taken by the agent"""
        self.logger.info(f"Action: {action} - {details}")
    
    def format_response(self, data: Any, format_type: str = "text") -> str:
        """Format response data"""
        if format_type == "json":
            return json.dumps(data, indent=2)
        elif format_type == "text":
            return str(data)
        else:
            return str(data)