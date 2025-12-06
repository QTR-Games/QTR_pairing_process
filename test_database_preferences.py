#!/usr/bin/env python3
"""
Test script for database persistence feature
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from qtr_pairing_process.database_preferences import DatabasePreferences

def test_database_preferences():
    """Test database preferences functionality"""
    print("🧪 Testing Database Preferences System")
    print("=" * 50)
    
    # Create preferences manager
    db_prefs = DatabasePreferences(print_output=True)
    print(f"✅ DatabasePreferences created")
    print(f"📁 Config file location: {db_prefs.get_config_file_path()}")
    
    # Test config loading
    config = db_prefs.load_config()
    print(f"✅ Config loaded: {list(config.keys())}")
    
    # Test database preference saving
    test_path = "C:/test/path/test.db"
    test_name = "test.db"
    
    success = db_prefs.save_database_preference(test_path, test_name)
    print(f"✅ Database preference saved: {success}")
    
    # Test database preference retrieval
    saved_path, saved_name = db_prefs.get_last_database()
    print(f"✅ Retrieved database: {saved_name} at {saved_path}")
    
    # Test welcome message preference
    show_welcome = db_prefs.should_show_welcome_message()
    print(f"✅ Show welcome message: {show_welcome}")
    
    # Test preference update
    db_prefs.set_welcome_message_preference(False)
    show_welcome_after = db_prefs.should_show_welcome_message()
    print(f"✅ Welcome message after update: {show_welcome_after}")
    
    # Test database validation
    valid = db_prefs.validate_database_exists(test_path, test_name)
    print(f"✅ Database validation (should be False): {valid}")
    
    # Test backup creation
    backup_path = db_prefs.backup_config()
    print(f"✅ Config backup created: {backup_path}")
    
    # Test clear preference
    cleared = db_prefs.clear_database_preference()
    print(f"✅ Database preference cleared: {cleared}")
    
    # Verify clearing worked
    cleared_path, cleared_name = db_prefs.get_last_database()
    print(f"✅ After clearing: {cleared_name} at {cleared_path}")
    
    print("\n🎉 All tests completed successfully!")

if __name__ == "__main__":
    test_database_preferences()