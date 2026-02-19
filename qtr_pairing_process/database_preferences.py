""" © Daniel P Raven and Matt Russell 2024 All Rights Reserved """

import json
import os
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple, Dict, Any
from tkinter import messagebox

class DatabasePreferences:
    """Manages database preferences and application configuration"""
    
    def __init__(self, print_output: bool = False):
        self.print_output = print_output
        self.config_file = Path(__file__).parent.parent / "KLIK_KLAK_KONFIG.json"
        self.logger = self._setup_logger()
        
    def _setup_logger(self) -> logging.Logger:
        """Setup logging for database preferences"""
        logger = logging.getLogger('database_preferences')
        logger.setLevel(logging.DEBUG if self.print_output else logging.INFO)
        
        # Create file handler for persistent logging
        log_file = Path(__file__).parent.parent / "qtr_pairing_process.log"
        handler = logging.FileHandler(log_file)
        handler.setLevel(logging.DEBUG)
        
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        
        # Add handler to logger if not already added
        if not logger.handlers:
            logger.addHandler(handler)
        
        return logger
    
    def _create_default_config(self) -> Dict[str, Any]:
        """Create default configuration structure"""
        return {
            "version": "1.0",
            "database": {
                "path": None,
                "name": None,
                "last_used": None
            },
            "ui_preferences": {
                "show_welcome_message": True,
                "rating_system": "1-5",
                "auto_tree_sync": False
            },
            "logging": {
                "level": "verbose",
                "enabled": True
            },
            "created": datetime.now().isoformat(),
            "last_modified": datetime.now().isoformat()
        }
    
    def load_config(self) -> Dict[str, Any]:
        """Load configuration from JSON file"""
        try:
            if not self.config_file.exists():
                self.logger.info(f"Config file does not exist: {self.config_file}")
                return self._create_default_config()
            
            with open(self.config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
                
            self.logger.debug(f"Config loaded successfully from: {self.config_file}")
            return config
            
        except json.JSONDecodeError as e:
            self.logger.error(f"JSON decode error in config file: {e}")
            messagebox.showerror("Configuration Error", 
                f"Configuration file is corrupted.\n"
                f"Using default settings.\n\n"
                f"Error: {str(e)}")
            return self._create_default_config()
            
        except Exception as e:
            self.logger.error(f"Unexpected error loading config: {e}")
            return self._create_default_config()
    
    def save_config(self, config: Dict[str, Any]) -> bool:
        """Save configuration to JSON file"""
        try:
            # Update modification timestamp
            config["last_modified"] = datetime.now().isoformat()
            
            # Ensure parent directory exists
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            
            self.logger.debug(f"Config saved successfully to: {self.config_file}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error saving config: {e}")
            messagebox.showerror("Configuration Error", 
                f"Could not save configuration.\n\n"
                f"Error: {str(e)}")
            return False
    
    def get_last_database(self) -> Tuple[Optional[str], Optional[str]]:
        """Get the last used database path and name"""
        config = self.load_config()
        db_config = config.get("database", {})
        
        path = db_config.get("path")
        name = db_config.get("name")
        
        if path and name:
            self.logger.info(f"Retrieved last database: {name} at {path}")
            return path, name
        else:
            self.logger.info("No previous database configuration found")
            return None, None
    
    def save_database_preference(self, path: str, name: str) -> bool:
        """Save database preference to config"""
        config = self.load_config()
        
        config["database"] = {
            "path": str(path),
            "name": str(name),
            "last_used": datetime.now().isoformat()
        }
        
        success = self.save_config(config)
        if success:
            self.logger.info(f"Database preference saved: {name} at {path}")
        else:
            self.logger.error(f"Failed to save database preference: {name}")
        
        return success
    
    def validate_database_exists(self, path: str, name: str) -> bool:
        """Check if database file exists and is accessible"""
        try:
            # Construct full path from directory path and filename
            full_path = Path(path) / name
            if full_path.exists() and full_path.is_file():
                self.logger.debug(f"Database validation successful: {full_path}")
                return True
            else:
                self.logger.warning(f"Database file not found: {full_path}")
                return False
                
        except Exception as e:
            self.logger.error(f"Database validation error for {path}/{name}: {e}")
            return False
    
    def should_show_welcome_message(self) -> bool:
        """Check if welcome message should be shown"""
        config = self.load_config()
        return config.get("ui_preferences", {}).get("show_welcome_message", True)
    
    def set_welcome_message_preference(self, show: bool) -> bool:
        """Set welcome message preference"""
        config = self.load_config()
        
        if "ui_preferences" not in config:
            config["ui_preferences"] = {}
        
        config["ui_preferences"]["show_welcome_message"] = show
        
        success = self.save_config(config)
        if success:
            self.logger.info(f"Welcome message preference updated: {show}")
        
        return success
    
    def get_ui_preferences(self) -> Dict[str, Any]:
        """Get all UI preferences"""
        config = self.load_config()
        return config.get("ui_preferences", {})
    
    def get_auto_tree_sync(self) -> bool:
        """Get auto tree sync preference (default: False)"""
        config = self.load_config()
        return config.get("ui_preferences", {}).get("auto_tree_sync", False)
    
    def set_auto_tree_sync(self, enabled: bool) -> bool:
        """Set auto tree sync preference"""
        config = self.load_config()
        
        if "ui_preferences" not in config:
            config["ui_preferences"] = {}
        
        config["ui_preferences"]["auto_tree_sync"] = enabled
        
        success = self.save_config(config)
        if success:
            self.logger.info(f"Auto tree sync preference updated: {enabled}")
        
        return success
    
    def update_ui_preferences(self, preferences: Dict[str, Any]) -> bool:
        """Update UI preferences"""
        config = self.load_config()
        
        if "ui_preferences" not in config:
            config["ui_preferences"] = {}
        
        config["ui_preferences"].update(preferences)
        
        success = self.save_config(config)
        if success:
            self.logger.info(f"UI preferences updated: {list(preferences.keys())}")
        
        return success
    
    def clear_database_preference(self) -> bool:
        """Clear saved database preference"""
        config = self.load_config()
        
        config["database"] = {
            "path": None,
            "name": None,
            "last_used": None
        }
        
        success = self.save_config(config)
        if success:
            self.logger.info("Database preference cleared")
        
        return success
    
    def get_config_file_path(self) -> str:
        """Get the full path to the config file"""
        return str(self.config_file.absolute())
    
    def backup_config(self) -> Optional[str]:
        """Create a backup of the current config file"""
        try:
            if not self.config_file.exists():
                return None
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = self.config_file.with_suffix(f'.backup_{timestamp}.json')
            
            import shutil
            shutil.copy2(self.config_file, backup_file)
            
            self.logger.info(f"Config backup created: {backup_file}")
            return str(backup_file)
            
        except Exception as e:
            self.logger.error(f"Failed to create config backup: {e}")
            return None