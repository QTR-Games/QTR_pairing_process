""" © Daniel P Raven and Matt Russell 2024 All Rights Reserved """

import logging
import sys
from pathlib import Path
from typing import Optional
from datetime import datetime


class AppLogger:
    """
    Centralized logging configuration for QTR Pairing Process
    Reads logging preferences from KLIK_KLAK_KONFIG.json
    """
    
    _instance: Optional['AppLogger'] = None
    _initialized: bool = False
    
    def __new__(cls):
        """Singleton pattern to ensure only one logger configuration exists"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize the application logger"""
        if not AppLogger._initialized:
            self.config = self._load_config()
            self.log_file = Path(__file__).parent.parent / "qtr_pairing_process.log"
            self._setup_logging()
            AppLogger._initialized = True
    
    def _load_config(self) -> dict:
        """Load logging configuration from KLIK_KLAK_KONFIG.json"""
        try:
            import json
            config_file = Path(__file__).parent.parent / "KLIK_KLAK_KONFIG.json"
            
            if config_file.exists():
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    return config.get('logging', {})
            else:
                # Default config if file doesn't exist
                return {'level': 'verbose', 'enabled': True}
        except Exception as e:
            print(f"Warning: Could not load logging config: {e}. Using defaults.")
            return {'level': 'verbose', 'enabled': True}
    
    def _setup_logging(self):
        """Configure the root logger based on config settings"""
        # Check if logging is enabled
        if not self.config.get('enabled', True):
            # Disable all logging except CRITICAL
            logging.disable(logging.CRITICAL)
            return
        
        # Determine log level
        level_str = self.config.get('level', 'verbose').lower()
        if level_str == 'verbose':
            log_level = logging.DEBUG
        else:  # 'normal' or any other value
            log_level = logging.INFO
        
        # Get root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(log_level)
        
        # Clear existing handlers to avoid duplicates
        root_logger.handlers.clear()
        
        # Create formatters
        verbose_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        simple_formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # File handler - always verbose
        try:
            file_handler = logging.FileHandler(self.log_file, encoding='utf-8')
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(verbose_formatter)
            root_logger.addHandler(file_handler)
        except Exception as e:
            print(f"Warning: Could not create log file: {e}")
        
        # Console handler - respects level setting
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(log_level)
        
        # Use simple formatter for console if not verbose
        if level_str == 'verbose':
            console_handler.setFormatter(verbose_formatter)
        else:
            console_handler.setFormatter(simple_formatter)
        
        root_logger.addHandler(console_handler)
        
        # Log initialization
        root_logger.info("=" * 60)
        root_logger.info(f"QTR Pairing Process - Logging initialized")
        root_logger.info(f"Log level: {level_str.upper()} ({logging.getLevelName(log_level)})")
        root_logger.info(f"Log file: {self.log_file}")
        root_logger.info("=" * 60)
    
    def get_logger(self, name: str) -> logging.Logger:
        """
        Get a logger instance for a specific module
        
        Args:
            name: Usually __name__ of the calling module
            
        Returns:
            Configured logger instance
        """
        return logging.getLogger(name)
    
    @staticmethod
    def reload_config():
        """Reload logging configuration from config file"""
        if AppLogger._instance:
            AppLogger._instance.config = AppLogger._instance._load_config()
            AppLogger._instance._setup_logging()
            logging.info("Logging configuration reloaded")
    
    @staticmethod
    def is_enabled() -> bool:
        """Check if logging is currently enabled"""
        if AppLogger._instance:
            return AppLogger._instance.config.get('enabled', True)
        return True
    
    @staticmethod
    def get_log_level() -> str:
        """Get current log level setting"""
        if AppLogger._instance:
            return AppLogger._instance.config.get('level', 'verbose')
        return 'verbose'


# Initialize the logger when module is imported
_app_logger = AppLogger()


def get_logger(name: str = __name__) -> logging.Logger:
    """
    Convenience function to get a logger instance
    
    Usage:
        from qtr_pairing_process.app_logger import get_logger
        logger = get_logger(__name__)
        logger.info("This is an info message")
        logger.error("This is an error message")
    
    Args:
        name: Logger name (typically __name__ of calling module)
    
    Returns:
        Configured logger instance
    """
    return _app_logger.get_logger(name)


def reload_logging_config():
    """
    Reload logging configuration from config file
    Call this after changing logging preferences in KLIK_KLAK_KONFIG.json
    """
    AppLogger.reload_config()
