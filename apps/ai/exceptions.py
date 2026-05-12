"""
Custom exceptions for Friday AI service.
"""


class AIServiceDisabledError(Exception):
    """Raised when AI service is globally disabled."""


class AIBudgetExceededError(Exception):
    """Raised when user's daily token budget is exhausted."""


class AIProviderError(Exception):
    """Raised when all configured providers fail."""
