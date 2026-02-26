# Centralized Logging Implementation Guide

**Date:** January 8, 2026  
**Topic:** Application-Wide Logging System  
**Purpose:** Learning resource for implementing production-ready, config-driven logging

---

## Overview

This document explains how QTR Pairing Process transitioned from scattered `print()` statements to a centralized, configuration-driven logging system that integrates with the application's `KLIK_KLAK_KONFIG.json` preferences.

## The Problem

### Before Implementation

**Issues with the original approach:**
1. **Inconsistent output** - Mix of `print()` statements throughout codebase
2. **No log persistence** - Output disappeared after closing terminal
3. **No verbosity control** - All messages printed at same level
4. **Unused config** - `KLIK_KLAK_KONFIG.json` had logging settings that weren't used
5. **Difficult debugging** - No timestamps, file locations, or structured format
6. **Production challenges** - Couldn't disable debug output in production

### Example of Old Code
```python
def select_database(self):
    # Using print statements
    print(f"Auto-loaded last database: {self.db_name} from {self.db_path}")
    print(f"Last used database not found: {last_name} at {last_path}")
    print("Showing database selector...")
```

## The Solution

### Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                  KLIK_KLAK_KONFIG.json                  │
│  "logging": {                                           │
│    "level": "verbose",      ← User configurable        │
│    "enabled": true          ← Can disable all logging  │
│  }                                                      │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│              app_logger.py (Singleton)                  │
│                                                         │
│  • Reads config on startup                             │
│  • Configures root logger                              │
│  • Provides get_logger() function                      │
│  • Supports runtime reload                             │
└────────────────────┬────────────────────────────────────┘
                     │
        ┌────────────┴────────────┐
        │                         │
        ▼                         ▼
┌─────────────────┐      ┌─────────────────┐
│ Console Handler │      │  File Handler   │
│  (stdout)       │      │  (.log file)    │
│                 │      │                 │
│ • INFO/DEBUG    │      │ • Always DEBUG  │
│ • User sees     │      │ • Persistent    │
└─────────────────┘      └─────────────────┘
```

### Implementation Components

#### 1. **AppLogger Class** (`qtr_pairing_process/app_logger.py`)

**Design Pattern: Singleton**
- Ensures only one logging configuration exists
- Prevents duplicate handlers
- Provides centralized control

```python
class AppLogger:
    _instance: Optional['AppLogger'] = None
    _initialized: bool = False
    
    def __new__(cls):
        """Singleton pattern"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
```

**Key Methods:**

1. **`_load_config()`** - Reads from KLIK_KLAK_KONFIG.json
2. **`_setup_logging()`** - Configures root logger based on config
3. **`get_logger(name)`** - Returns module-specific logger
4. **`reload_config()`** - Reloads config without restart

#### 2. **Configuration-Driven Behavior**

**Config Options:**
```json
{
  "logging": {
    "level": "verbose",  // "verbose" or "normal"
    "enabled": true      // true or false
  }
}
```

**Behavior Mapping:**

| Config Setting | Python Log Level | Console Output | File Output |
|---------------|------------------|----------------|-------------|
| `level: "verbose"` | DEBUG | Detailed with file:line | All levels |
| `level: "normal"` | INFO | Basic messages | All levels |
| `enabled: false` | CRITICAL (disabled) | None | None |

#### 3. **Formatter Patterns**

**Verbose Mode (DEBUG):**
```
%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s

Example:
2026-01-08 14:30:15 - qtr_pairing_process.ui_manager - INFO - [ui_manager.py:82] - UiManager initializing...
```

**Normal Mode (INFO):**
```
%(asctime)s - %(levelname)s - %(message)s

Example:
2026-01-08 14:30:15 - INFO - UiManager initializing...
```

## Usage Patterns

### Basic Usage

```python
# 1. Import the logger
from qtr_pairing_process.app_logger import get_logger

# 2. Create module-specific logger (typically at module level)
logger = get_logger(__name__)

# 3. Use throughout your code
logger.debug("Detailed debugging info")
logger.info("General information")
logger.warning("Something unexpected but handled")
logger.error("An error occurred")
logger.critical("Critical system failure")
```

### Migration Pattern

**Before:**
```python
def some_function():
    try:
        # do something
        print(f"Successfully completed task")
    except Exception as e:
        print(f"Error: {e}")
```

**After:**
```python
def some_function():
    try:
        # do something
        logger.info("Successfully completed task")
    except Exception as e:
        logger.error(f"Error occurred", exc_info=True)  # Includes stack trace
```

### Advanced Usage

#### Including Exception Details

```python
try:
    risky_operation()
except Exception as e:
    # exc_info=True includes full stack trace in log
    logger.error(f"Operation failed: {e}", exc_info=True)
```

#### Conditional Logging

```python
if logger.isEnabledFor(logging.DEBUG):
    # Only compute expensive debug info if debug logging is on
    debug_info = compute_expensive_debug_data()
    logger.debug(f"Debug data: {debug_info}")
```

#### Context-Rich Messages

```python
logger.info(
    "Database loaded",
    extra={
        'database_name': db_name,
        'record_count': count,
        'load_time_ms': elapsed_ms
    }
)
```

## Best Practices Learned

### 1. **Use Appropriate Log Levels**

| Level | Use When | Example |
|-------|----------|---------|
| DEBUG | Detailed diagnostic info | Variable values, function entry/exit |
| INFO | General informational messages | "User logged in", "File saved" |
| WARNING | Unexpected but handled situation | "Config missing, using defaults" |
| ERROR | Error that caused operation to fail | "Database connection failed" |
| CRITICAL | Severe error, app may crash | "Out of memory" |

### 2. **Logger Naming Convention**

Always use `__name__` when creating loggers:
```python
logger = get_logger(__name__)
```

This creates hierarchical loggers like:
- `qtr_pairing_process.ui_manager`
- `qtr_pairing_process.database_preferences`
- `qtr_pairing_process.tree_generator`

Benefits:
- Easy to filter logs by module
- Can set different log levels per module if needed
- Clear source of each message

### 3. **Don't Log Sensitive Data**

**Bad:**
```python
logger.info(f"User password: {password}")  # DON'T DO THIS
```

**Good:**
```python
logger.info("User authenticated successfully")
```

### 4. **Log Entry and Exit for Complex Operations**

```python
def complex_operation(data):
    logger.debug(f"Starting complex_operation with {len(data)} items")
    try:
        result = process(data)
        logger.debug(f"Completed complex_operation, result: {result}")
        return result
    except Exception as e:
        logger.error("complex_operation failed", exc_info=True)
        raise
```

### 5. **Use F-Strings for Lazy Evaluation**

**Preferred:**
```python
logger.debug(f"Processing {len(items)} items")  # Evaluated only if debug enabled
```

**Works but less efficient:**
```python
logger.debug("Processing %d items", len(items))  # Old % formatting
```

## Integration Points

### Startup Integration

```python
# qtr_pairing_process/ui_manager.py
from qtr_pairing_process.app_logger import get_logger

class UiManager:
    def __init__(self, ...):
        # Initialize logger early
        self.logger = get_logger(__name__)
        self.logger.info("UiManager initializing...")
        
        # Rest of initialization
```

### Database Operations

```python
def select_database(self):
    last_path, last_name = self.db_preferences.get_last_database()
    
    if last_path and last_name:
        if self.db_preferences.validate_database_exists(last_path, last_name):
            self.logger.info(f"Auto-loaded database: {last_name}")
            return
        else:
            self.logger.warning(f"Database not found: {last_name}")
```

### Error Handling

```python
def show_welcome_dialog(self):
    try:
        welcome = WelcomeDialog(self.root)
        show_again = welcome.show_welcome_message()
        self.db_preferences.set_welcome_message_preference(show_again)
    except Exception as e:
        self.logger.error("Error showing welcome dialog", exc_info=True)
```

## Testing the Logger

### Verify Configuration

```python
from qtr_pairing_process.app_logger import AppLogger

# Check current settings
print(f"Logging enabled: {AppLogger.is_enabled()}")
print(f"Log level: {AppLogger.get_log_level()}")
```

### Test Different Levels

```python
from qtr_pairing_process.app_logger import get_logger

logger = get_logger("test")

logger.debug("This is DEBUG")
logger.info("This is INFO")
logger.warning("This is WARNING")
logger.error("This is ERROR")
logger.critical("This is CRITICAL")
```

### Runtime Configuration Change

1. Edit `KLIK_KLAK_KONFIG.json`:
   ```json
   "logging": {
     "level": "normal",
     "enabled": true
   }
   ```

2. Reload without restarting:
   ```python
   from qtr_pairing_process.app_logger import reload_logging_config
   reload_logging_config()
   ```

## Log File Management

### Location
- **File**: `qtr_pairing_process.log` (in project root)
- **Encoding**: UTF-8 (supports international characters)
- **Format**: Always verbose (DEBUG level)

### Rotation (Future Enhancement)

Consider implementing log rotation when file grows large:

```python
from logging.handlers import RotatingFileHandler

# In _setup_logging()
file_handler = RotatingFileHandler(
    self.log_file,
    maxBytes=10*1024*1024,  # 10 MB
    backupCount=5,           # Keep 5 backup files
    encoding='utf-8'
)
```

## Common Patterns

### Pattern 1: Database Operations

```python
def load_data(self):
    self.logger.debug("Starting data load...")
    
    try:
        data = self.db_manager.fetch_data()
        self.logger.info(f"Loaded {len(data)} records")
        return data
    except Exception as e:
        self.logger.error("Data load failed", exc_info=True)
        raise
```

### Pattern 2: User Actions

```python
def on_button_click(self):
    self.logger.debug("Button clicked")
    
    try:
        result = self.perform_action()
        self.logger.info("Action completed successfully")
        return result
    except ValueError as e:
        self.logger.warning(f"Invalid input: {e}")
        self.show_error_dialog(str(e))
    except Exception as e:
        self.logger.error("Unexpected error", exc_info=True)
        self.show_error_dialog("An unexpected error occurred")
```

### Pattern 3: Configuration Changes

```python
def update_setting(self, key, value):
    self.logger.info(f"Updating setting: {key}")
    
    old_value = self.settings.get(key)
    self.settings[key] = value
    
    self.logger.debug(f"Setting '{key}' changed: {old_value} -> {value}")
    self.save_settings()
```

## Troubleshooting

### Issue: No Log Output

**Check:**
1. Is logging enabled in config?
   ```json
   "logging": {"enabled": true}
   ```
2. Is log level appropriate?
   - `normal` won't show DEBUG messages
   - `verbose` shows everything

### Issue: Duplicate Log Messages

**Cause:** Multiple handlers attached to logger

**Solution:** AppLogger singleton prevents this, but if you see duplicates:
```python
# Check handlers
logger = logging.getLogger()
print(f"Number of handlers: {len(logger.handlers)}")
```

### Issue: Log File Not Created

**Check:**
1. Write permissions in project directory
2. Path exists: `Path(__file__).parent.parent / "qtr_pairing_process.log"`
3. No file system errors in console

## Key Takeaways

### What We Learned

1. **Singleton Pattern** - Perfect for application-wide configuration
2. **Config-Driven Design** - User preferences control behavior
3. **Separation of Concerns** - Logging logic separate from business logic
4. **Module Hierarchy** - `__name__` creates organized logger tree
5. **Multiple Outputs** - Console for users, file for debugging

### Benefits Achieved

✅ **Consistent** - All output follows same format  
✅ **Persistent** - Logs saved to file for later analysis  
✅ **Configurable** - Users control verbosity  
✅ **Debuggable** - Stack traces and file locations included  
✅ **Production-Ready** - Can disable for performance  
✅ **Professional** - Follows Python logging best practices

### Python Logging Concepts Demonstrated

- **Logger Hierarchy** - Dot-separated names create tree structure
- **Handlers** - Where logs go (file, console, network, etc.)
- **Formatters** - How logs are formatted
- **Levels** - Filtering by severity
- **Singleton Pattern** - Single configuration instance
- **Context Managers** - Clean resource handling

## References

### Python Documentation
- [Logging HOWTO](https://docs.python.org/3/howto/logging.html)
- [Logging Cookbook](https://docs.python.org/3/howto/logging-cookbook.html)
- [logging module API](https://docs.python.org/3/library/logging.html)

### Related Files
- [`qtr_pairing_process/app_logger.py`](../../qtr_pairing_process/app_logger.py) - Implementation
- [`qtr_pairing_process/ui_manager.py`](../../qtr_pairing_process/ui_manager.py) - Usage examples
- [`KLIK_KLAK_KONFIG.json`](../../KLIK_KLAK_KONFIG.json) - Configuration

### Design Patterns
- **Singleton Pattern** - Ensures single instance
- **Factory Pattern** - `get_logger()` creates loggers
- **Configuration Pattern** - Externalized settings

## Next Steps

### For Full Migration

1. **Identify all print statements**
   ```bash
   grep -r "print(f" qtr_pairing_process/
   ```

2. **Replace systematically**
   - Error messages → `logger.error()`
   - Status updates → `logger.info()`
   - Debug output → `logger.debug()`

3. **Test each module**
   - Verify logs appear in file
   - Check console output
   - Test with `enabled: false`

### Future Enhancements

1. **Add log rotation** - Prevent unbounded file growth
2. **Add network logging** - Send logs to central server
3. **Add structured logging** - JSON format for parsing
4. **Add log viewer** - UI for browsing logs
5. **Per-module levels** - Different verbosity per module

---

**Document Status:** Complete  
**Last Updated:** January 8, 2026  
**Related Issues:** Config file utilization, production-ready logging
