"""
Data Sanitization and Validation Utility
Provides robust input validation and sanitization for user data to prevent
SQL injection attacks and handle international characters properly.
"""
import re
import unicodedata
from typing import Optional, Union, List


class DataValidator:
    """Comprehensive data validation and sanitization for database operations"""
    
    # Dangerous SQL keywords and patterns
    SQL_INJECTION_PATTERNS = [
        r"'.*?'.*?'",  # Multiple quotes
        r"--|\/\*|\*\/",  # SQL comments
        r"\b(UNION|SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|EXECUTE)\b",  # SQL keywords
        r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]",  # Control characters
    ]
    
    # Allowed characters for names (including international and special characters)
    # Supports: letters, numbers, spaces, hyphens, apostrophes, periods, hash/pound (#),
    # parentheses, underscores, plus signs, ampersands, and various international characters
    # (accents, umlauts, cedillas, etc.)
    SAFE_NAME_PATTERN = re.compile(
        r"^[\w\s\-'\.#\(\)\+&àáâãäåæçèéêëìíîïðñòóôõöøùúûüýþÿ"
        r"\u0100-\u017f\u0180-\u024f\u1e00-\u1eff\u0370-\u03ff\u0400-\u04ff]+$",
        re.IGNORECASE | re.UNICODE
    )
    
    @staticmethod
    def sanitize_text_input(text: str, max_length: int = 255, allow_empty: bool = False) -> Optional[str]:
        """
        Sanitize text input for safe database storage
        
        Args:
            text: Input text to sanitize
            max_length: Maximum allowed length
            allow_empty: Whether to allow empty strings
            
        Returns:
            Sanitized text or None if invalid
        """
        if text is None:
            return None if allow_empty else None
            
        # Convert to string and strip whitespace
        text = str(text).strip()
        
        # Check for empty after stripping
        if not text:
            return "" if allow_empty else None
            
        # Check length
        if len(text) > max_length:
            raise ValueError(f"Text exceeds maximum length of {max_length} characters")
            
        # Normalize unicode characters
        text = unicodedata.normalize('NFC', text)
        
        # Check for SQL injection patterns
        for pattern in DataValidator.SQL_INJECTION_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                raise ValueError(f"Input contains potentially dangerous characters or SQL keywords")
                
        # Validate against safe character pattern
        if not DataValidator.SAFE_NAME_PATTERN.match(text):
            raise ValueError(
                "Input contains invalid characters. "
                "Only letters, numbers, spaces, hyphens, apostrophes, periods, "
                "hash symbols (#), parentheses, plus signs, ampersands, and international characters are allowed."
            )
            
        return text
    
    @staticmethod
    def validate_team_name(team_name: str) -> str:
        """
        Validate and sanitize team name
        
        Args:
            team_name: Team name to validate
            
        Returns:
            Sanitized team name
            
        Raises:
            ValueError: If team name is invalid
        """
        sanitized = DataValidator.sanitize_text_input(team_name, max_length=100, allow_empty=False)
        if sanitized is None:
            raise ValueError("Team name cannot be empty")
            
        # Additional team name specific validation
        if len(sanitized) < 2:
            raise ValueError("Team name must be at least 2 characters long")
            
        # Check for reserved names
        reserved_names = ['NULL', 'NONE', 'UNDEFINED', 'UNKNOWN']
        if sanitized.upper() in reserved_names:
            raise ValueError(f"'{sanitized}' is a reserved name and cannot be used")
            
        return sanitized
    
    @staticmethod
    def validate_player_name(player_name: str) -> str:
        """
        Validate and sanitize player name
        
        Args:
            player_name: Player name to validate
            
        Returns:
            Sanitized player name
            
        Raises:
            ValueError: If player name is invalid
        """
        sanitized = DataValidator.sanitize_text_input(player_name, max_length=100, allow_empty=False)
        if sanitized is None:
            raise ValueError("Player name cannot be empty")
            
        # Additional player name specific validation
        if len(sanitized) < 1:
            raise ValueError("Player name must be at least 1 character long")
            
        return sanitized
    
    @staticmethod
    def validate_scenario_name(scenario_name: str) -> str:
        """
        Validate and sanitize scenario name
        
        Args:
            scenario_name: Scenario name to validate
            
        Returns:
            Sanitized scenario name
            
        Raises:
            ValueError: If scenario name is invalid
        """
        sanitized = DataValidator.sanitize_text_input(scenario_name, max_length=200, allow_empty=False)
        if sanitized is None:
            raise ValueError("Scenario name cannot be empty")
            
        return sanitized
    
    @staticmethod
    def validate_integer(value: Union[str, int], min_value: Optional[int] = None, max_value: Optional[int] = None) -> int:
        """
        Validate and convert integer input
        
        Args:
            value: Value to validate
            min_value: Minimum allowed value
            max_value: Maximum allowed value
            
        Returns:
            Validated integer
            
        Raises:
            ValueError: If value is invalid
        """
        try:
            int_value = int(value)
        except (ValueError, TypeError):
            raise ValueError("Value must be a valid integer")
            
        if min_value is not None and int_value < min_value:
            raise ValueError(f"Value must be at least {min_value}")
            
        if max_value is not None and int_value > max_value:
            raise ValueError(f"Value must be at most {max_value}")
            
        return int_value
    
    @staticmethod
    def validate_rating(rating: Union[str, int], rating_system: str = "1-5") -> int:
        """
        Validate rating value based on rating system
        
        Args:
            rating: Rating value to validate
            rating_system: Rating system ("1-3", "1-5", "1-10")
            
        Returns:
            Validated rating
            
        Raises:
            ValueError: If rating is invalid
        """
        # Define valid ranges for each rating system
        valid_ranges = {
            "1-3": (1, 3),
            "1-5": (1, 5),
            "1-10": (1, 10)
        }
        
        if rating_system not in valid_ranges:
            raise ValueError(f"Unknown rating system: {rating_system}")
            
        min_val, max_val = valid_ranges[rating_system]
        return DataValidator.validate_integer(rating, min_value=min_val, max_value=max_val)
    
    @staticmethod
    def validate_batch_names(names: List[str], validator_func) -> List[str]:
        """
        Validate a batch of names using the specified validator function
        
        Args:
            names: List of names to validate
            validator_func: Function to use for validation
            
        Returns:
            List of validated names
            
        Raises:
            ValueError: If any name is invalid
        """
        validated_names = []
        
        for i, name in enumerate(names):
            try:
                validated_name = validator_func(name)
                validated_names.append(validated_name)
            except ValueError as e:
                raise ValueError(f"Invalid name at position {i+1}: {e}")
                
        # Check for duplicates
        seen = set()
        for i, name in enumerate(validated_names):
            name_lower = name.lower()
            if name_lower in seen:
                raise ValueError(f"Duplicate name found: '{name}' at position {i+1}")
            seen.add(name_lower)
            
        return validated_names
    
    @staticmethod
    def escape_for_display(text: str) -> str:
        """
        Escape text for safe display in UI components
        
        Args:
            text: Text to escape
            
        Returns:
            Escaped text safe for display
        """
        if not text:
            return ""
            
        # HTML entity encoding for common characters
        replacements = {
            '<': '&lt;',
            '>': '&gt;',
            '&': '&amp;',
            '"': '&quot;',
            "'": '&#x27;'
        }
        
        escaped = text
        for char, entity in replacements.items():
            escaped = escaped.replace(char, entity)
            
        return escaped
    
    @staticmethod
    def test_validation():
        """Test the validation functions with various inputs"""
        test_cases = [
            # Valid cases
            ("John's Team", DataValidator.validate_team_name, True),
            ("Devourer's Host", DataValidator.validate_player_name, True),
            ("Test Scenario", DataValidator.validate_scenario_name, True),
            ("João da Silva", DataValidator.validate_player_name, True),  # Portuguese
            ("François Müller", DataValidator.validate_player_name, True),  # French/German
            ("Москва United", DataValidator.validate_team_name, False),  # Cyrillic - should fail with current pattern
            
            # Invalid cases - SQL injection attempts
            ("'; DROP TABLE teams; --", DataValidator.validate_team_name, False),
            ("Robert'); DELETE FROM players; --", DataValidator.validate_player_name, False),
            ("Team' UNION SELECT * FROM users --", DataValidator.validate_team_name, False),
        ]
        
        print("🧪 Testing Data Validation...")
        
        for test_input, validator, should_pass in test_cases:
            try:
                result = validator(test_input)
                if should_pass:
                    print(f"✅ PASS: '{test_input}' → '{result}'")
                else:
                    print(f"❌ FAIL: '{test_input}' should have been rejected but passed")
            except ValueError as e:
                if not should_pass:
                    print(f"✅ PASS: '{test_input}' correctly rejected - {e}")
                else:
                    print(f"❌ FAIL: '{test_input}' should have passed but was rejected - {e}")
        
        print("🔐 Data validation tests completed!")


if __name__ == "__main__":
    DataValidator.test_validation()