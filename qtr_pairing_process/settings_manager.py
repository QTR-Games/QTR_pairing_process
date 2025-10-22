""" © Daniel P Raven and Matt Russell 2024 All Rights Reserved """

import os
import json
from .constants import DEFAULT_RATING_SYSTEM

class SettingsManager:
    """Manage application settings including rating system preferences"""
    
    def __init__(self, settings_file="qtr_settings.json"):
        self.settings_file = settings_file
        self.settings = self._load_settings()
    
    def _load_settings(self):
        """Load settings from file or create defaults"""
        default_settings = {
            'rating_system': DEFAULT_RATING_SYSTEM,
            'database_path': None,
            'last_team1': None,
            'last_team2': None,
            'window_geometry': None
        }
        
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, 'r') as f:
                    loaded_settings = json.load(f)
                    # Merge with defaults to ensure all keys exist
                    default_settings.update(loaded_settings)
                    return default_settings
            except (json.JSONDecodeError, IOError) as e:
                print(f"Error loading settings: {e}. Using defaults.")
                return default_settings
        else:
            return default_settings
    
    def save_settings(self):
        """Save current settings to file"""
        try:
            with open(self.settings_file, 'w') as f:
                json.dump(self.settings, f, indent=4)
        except IOError as e:
            print(f"Error saving settings: {e}")
    
    def get_rating_system(self):
        """Get current rating system setting"""
        return self.settings.get('rating_system', DEFAULT_RATING_SYSTEM)
    
    def set_rating_system(self, system):
        """Set rating system and save"""
        self.settings['rating_system'] = system
        self.save_settings()
    
    def get_setting(self, key, default=None):
        """Get any setting by key"""
        return self.settings.get(key, default)
    
    def set_setting(self, key, value):
        """Set any setting and save"""
        self.settings[key] = value
        self.save_settings()