"""
context.py - Context classes for OpenAI Agent SDK local context
"""
from dataclasses import dataclass
from typing import Optional
from datetime import date

@dataclass
class SessionContext:
    """Context class for session-related operations"""
    session_date: str  # ISO format date string (YYYY-MM-DD)
    
    def get_date_object(self) -> date:
        """Convert session_date string to date object
        
        Some functions in the codebase require a date object rather than a string.
        This method handles the conversion and provides error handling if the
        session_date string is not in a valid ISO format.
        
        Returns:
            date: A date object representing the session date
        """
        try:
            return date.fromisoformat(self.session_date)
        except ValueError:
            # Fallback to today if invalid format
            return date.today()
