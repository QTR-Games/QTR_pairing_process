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
    
    def __init__(self, print_output: bool = False, config_file: Optional[Path] = None):
        self.print_output = print_output
        self.config_file = (
            Path(config_file)
            if config_file is not None
            else Path(__file__).parent.parent / "KLIK_KLAK_KONFIG.json"
        )
        self.max_config_backups = 3
        self.logger = self._setup_logger()

    def _normalize_database_reference(self, path: Optional[str], name: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
        """Normalize database reference into directory path + filename.

        Accepts either:
        - path=directory, name=filename
        - path=full_file_path, name optional
        """
        if not path and not name:
            return None, None

        raw_path = str(path).strip() if path is not None else ""
        raw_name = str(name).strip() if name is not None else ""

        if not raw_path:
            return None, raw_name or None

        path_obj = Path(raw_path)

        # If the provided path already looks like a DB file path, split it.
        if path_obj.suffix.lower() == ".db":
            return str(path_obj.parent), path_obj.name

        # If path is a directory and name is provided, keep as-is.
        if raw_name:
            return raw_path, raw_name

        return raw_path, None
        
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
                "auto_tree_sync": False,
                "tree_autogen_enabled": True,
                "lazy_sort_on_expand": False,
                "lazy_sort_mode": "strict",
                "right_column_panel": "notes",
                "pairing_plan_notes": "",
                "matchup_output_format": "standard",
                "perf_logging_enabled": False
            },
            "strategic_preferences": self._get_default_strategic_preferences(),
            "logging": {
                "level": "verbose",
                "enabled": True
            },
            "created": datetime.now().isoformat(),
            "last_modified": datetime.now().isoformat()
        }

    def _get_default_strategic_preferences(self) -> Dict[str, Any]:
        """Return default strategic/v2 scoring preferences."""
        return {
            "cumulative2": {
                "alpha": 0.80
            },
            "confidence2": {
                "k": 0.85,
                "u": 12.0
            },
            "resistance2": {
                "beta": 1.0,
                "gamma": 2.0
            },
            "strategic3": {
                "weights": [0.40, 0.35, 0.25],
                "rho": 0.20,
                "lam": 0.30,
                "round_win_guardrail_strength": "medium",
                "tie_break_order": "confidence_then_cumulative",
                "auto_sort_after_generate": True,
                "auto_sort_toggle_enabled": True,
                "persistent_memo_enabled": True,
                "persistent_memo_max_entries": 50000
            },
            "bus": {
                "threshold_policy": "scenario_dependent",
                "global_threshold": 60,
                "scenario_thresholds": {},
                "depth_thresholds": {
                    "1": 65,
                    "2": 62,
                    "3": 58,
                    "4": 55,
                    "5": 52
                }
            }
        }

    def _clamp(self, value: Any, min_value: float, max_value: float, default_value: float) -> float:
        """Convert to float and clamp safely."""
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            numeric = float(default_value)
        return max(min_value, min(max_value, numeric))

    def get_strategic_preferences(self) -> Dict[str, Any]:
        """Get validated strategic/v2 preferences merged with defaults."""
        config = self.load_config()
        defaults = self._get_default_strategic_preferences()
        raw = config.get("strategic_preferences", {})

        cumulative2 = raw.get("cumulative2", {})
        confidence2 = raw.get("confidence2", {})
        resistance2 = raw.get("resistance2", {})
        strategic3 = raw.get("strategic3", {})
        bus = raw.get("bus", {})

        validated = {
            "cumulative2": {
                "alpha": self._clamp(cumulative2.get("alpha", defaults["cumulative2"]["alpha"]), 0.0, 1.0, defaults["cumulative2"]["alpha"])
            },
            "confidence2": {
                "k": self._clamp(confidence2.get("k", defaults["confidence2"]["k"]), 0.0, 5.0, defaults["confidence2"]["k"]),
                "u": self._clamp(confidence2.get("u", defaults["confidence2"]["u"]), 0.0, 100.0, defaults["confidence2"]["u"])
            },
            "resistance2": {
                "beta": self._clamp(resistance2.get("beta", defaults["resistance2"]["beta"]), 0.0, 10.0, defaults["resistance2"]["beta"]),
                "gamma": self._clamp(resistance2.get("gamma", defaults["resistance2"]["gamma"]), 0.0, 10.0, defaults["resistance2"]["gamma"])
            },
            "strategic3": {
                "weights": strategic3.get("weights", defaults["strategic3"]["weights"]),
                "rho": self._clamp(strategic3.get("rho", defaults["strategic3"]["rho"]), 0.0, 5.0, defaults["strategic3"]["rho"]),
                "lam": self._clamp(strategic3.get("lam", defaults["strategic3"]["lam"]), 0.0, 5.0, defaults["strategic3"]["lam"]),
                "round_win_guardrail_strength": strategic3.get("round_win_guardrail_strength", defaults["strategic3"]["round_win_guardrail_strength"]),
                "tie_break_order": strategic3.get("tie_break_order", defaults["strategic3"]["tie_break_order"]),
                "auto_sort_after_generate": bool(strategic3.get("auto_sort_after_generate", defaults["strategic3"]["auto_sort_after_generate"])),
                "auto_sort_toggle_enabled": bool(strategic3.get("auto_sort_toggle_enabled", defaults["strategic3"]["auto_sort_toggle_enabled"])),
                "persistent_memo_enabled": bool(strategic3.get("persistent_memo_enabled", defaults["strategic3"]["persistent_memo_enabled"])),
                "persistent_memo_max_entries": int(self._clamp(strategic3.get("persistent_memo_max_entries", defaults["strategic3"]["persistent_memo_max_entries"]), 1000.0, 250000.0, defaults["strategic3"]["persistent_memo_max_entries"]))
            },
            "bus": {
                "threshold_policy": bus.get("threshold_policy", defaults["bus"]["threshold_policy"]),
                "global_threshold": int(self._clamp(bus.get("global_threshold", defaults["bus"]["global_threshold"]), 0.0, 100.0, defaults["bus"]["global_threshold"])),
                "scenario_thresholds": bus.get("scenario_thresholds", defaults["bus"]["scenario_thresholds"]),
                "depth_thresholds": bus.get("depth_thresholds", defaults["bus"]["depth_thresholds"])
            }
        }

        # Ensure strategic weights are a valid 3-value list that sums to 1.
        weights = validated["strategic3"]["weights"]
        if not isinstance(weights, list) or len(weights) != 3:
            weights = defaults["strategic3"]["weights"]
        safe_weights = [
            self._clamp(weights[0], 0.0, 1.0, defaults["strategic3"]["weights"][0]),
            self._clamp(weights[1], 0.0, 1.0, defaults["strategic3"]["weights"][1]),
            self._clamp(weights[2], 0.0, 1.0, defaults["strategic3"]["weights"][2]),
        ]
        total = sum(safe_weights)
        if total <= 0:
            safe_weights = defaults["strategic3"]["weights"]
        else:
            safe_weights = [w / total for w in safe_weights]
        validated["strategic3"]["weights"] = safe_weights

        return validated

    def set_strategic_preferences(self, preferences: Dict[str, Any]) -> bool:
        """Update strategic/v2 preferences and persist config."""
        config = self.load_config()
        existing = config.get("strategic_preferences", self._get_default_strategic_preferences())

        # Shallow merge by section for predictable behavior.
        merged = dict(existing)
        for section, values in preferences.items():
            if isinstance(values, dict) and isinstance(merged.get(section), dict):
                section_dict = dict(merged[section])
                section_dict.update(values)
                merged[section] = section_dict
            else:
                merged[section] = values

        config["strategic_preferences"] = merged
        success = self.save_config(config)
        if success:
            self.logger.info("Strategic preferences updated")
        return success
    
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
        
        path, name = self._normalize_database_reference(
            db_config.get("path"),
            db_config.get("name"),
        )
        
        if path and name:
            self.logger.info(f"Retrieved last database: {name} at {path}")
            return path, name
        else:
            self.logger.info("No previous database configuration found")
            return None, None
    
    def save_database_preference(self, path: str, name: str) -> bool:
        """Save database preference to config"""
        config = self.load_config()
        normalized_path, normalized_name = self._normalize_database_reference(path, name)
        if not normalized_path or not normalized_name:
            self.logger.error(f"Invalid database preference input: path={path}, name={name}")
            return False
        
        config["database"] = {
            "path": str(normalized_path),
            "name": str(normalized_name),
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
            normalized_path, normalized_name = self._normalize_database_reference(path, name)
            if not normalized_path or not normalized_name:
                self.logger.warning(f"Database validation failed due to invalid reference: {path}/{name}")
                return False

            # Construct full path from directory path and filename
            full_path = Path(normalized_path) / normalized_name
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
    
    def get_matchup_output_format(self) -> str:
        """Get matchup output format preference (standard or verbose)"""
        config = self.load_config()
        return config.get("ui_preferences", {}).get("matchup_output_format", "standard")
    
    def set_matchup_output_format(self, format_type: str) -> bool:
        """Set matchup output format preference
        
        Args:
            format_type: Either 'standard' or 'verbose'
        """
        if format_type not in ['standard', 'verbose']:
            raise ValueError("Format must be 'standard' or 'verbose'")
        
        config = self.load_config()
        
        if "ui_preferences" not in config:
            config["ui_preferences"] = {}
        
        config["ui_preferences"]["matchup_output_format"] = format_type
        
        success = self.save_config(config)
        if success:
            self.logger.info(f"Matchup output format updated: {format_type}")
        
        return success
    
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

    def get_pairing_plan_notes(self) -> str:
        """Get persisted pairing plan notes."""
        notes = self.get_ui_preferences().get("pairing_plan_notes", "")
        return notes if isinstance(notes, str) else ""

    def set_pairing_plan_notes(self, notes: str) -> bool:
        """Persist pairing plan notes."""
        config = self.load_config()

        if "ui_preferences" not in config:
            config["ui_preferences"] = {}

        config["ui_preferences"]["pairing_plan_notes"] = notes if isinstance(notes, str) else ""
        success = self.save_config(config)
        if success:
            self.logger.info("Pairing plan notes updated")
        return success
    
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


    def get_tree_autogen_enabled(self) -> bool:
        """Get tree auto-generation preference (default: False)."""
        config = self.load_config()
        return bool(config.get("ui_preferences", {}).get("tree_autogen_enabled", False))

    def set_tree_autogen_enabled(self, enabled: bool) -> bool:
        """Set tree auto-generation preference."""
        config = self.load_config()

        if "ui_preferences" not in config:
            config["ui_preferences"] = {}

        config["ui_preferences"]["tree_autogen_enabled"] = bool(enabled)
        success = self.save_config(config)
        if success:
            self.logger.info(f"Tree auto-generation preference updated: {enabled}")
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

            backup_files = self._list_config_backups()
            if backup_files:
                newest_backup = backup_files[0]
                try:
                    # Avoid creating duplicate backups when config content is unchanged.
                    if newest_backup.read_bytes() == self.config_file.read_bytes():
                        self._prune_config_backups(self.max_config_backups)
                        self.logger.info(f"Config backup skipped (unchanged): {newest_backup}")
                        return str(newest_backup)
                except Exception:
                    # If any read/compare issue occurs, fall through to normal backup creation.
                    pass
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            backup_file = self.config_file.with_suffix(f'.backup_{timestamp}.json')
            
            import shutil
            shutil.copy2(self.config_file, backup_file)
            self._prune_config_backups(self.max_config_backups)
            
            self.logger.info(f"Config backup created: {backup_file}")
            return str(backup_file)
            
        except Exception as e:
            self.logger.error(f"Failed to create config backup: {e}")
            return None

    def _list_config_backups(self) -> list[Path]:
        pattern = f"{self.config_file.stem}.backup_*.json"
        candidates = list(self.config_file.parent.glob(pattern))
        candidates.sort(key=lambda path: path.stat().st_mtime, reverse=True)
        return candidates

    def _prune_config_backups(self, keep_count: int):
        keep_count = max(1, int(keep_count))
        backups = self._list_config_backups()
        for old_backup in backups[keep_count:]:
            try:
                old_backup.unlink(missing_ok=True)
            except Exception:
                pass