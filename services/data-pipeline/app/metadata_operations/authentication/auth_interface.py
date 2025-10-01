"""
Abstract interface for authentication providers
"""

from abc import ABC, abstractmethod
from typing import Dict, Optional
from ..models import AuthenticationResult, AuthenticationType


class AuthenticationInterface(ABC):
    """Abstract base class for authentication providers"""
    
    @abstractmethod
    async def authenticate(self) -> AuthenticationResult:
        """
        Perform authentication
        
        Returns:
            Authentication result with token and metadata
        """
        pass
    
    @abstractmethod
    def get_auth_headers(self) -> Dict[str, str]:
        """
        Get authentication headers for API requests
        
        Returns:
            Dictionary of headers to include in requests
        """
        pass
    
    @abstractmethod
    async def refresh_token(self) -> AuthenticationResult:
        """
        Refresh the authentication token if supported
        
        Returns:
            New authentication result
        """
        pass
    
    @abstractmethod
    def is_token_valid(self) -> bool:
        """
        Check if current token is valid
        
        Returns:
            True if token is valid, False otherwise
        """
        pass
    
    @property
    @abstractmethod
    def auth_type(self) -> AuthenticationType:
        """Get the authentication type"""
        pass
