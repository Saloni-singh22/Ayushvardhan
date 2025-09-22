"""
WHO ICD-11 API OAuth2 Authentication Service
Handles authentication with WHO ICD API using client credentials flow
"""

import asyncio
from typing import Optional, Dict, Any
import httpx
from datetime import datetime, timedelta
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)


class WHOAPIAuthService:
    """
    OAuth2 authentication service for WHO ICD-11 API
    Manages access tokens using client credentials flow
    """
    
    def __init__(self):
        self.client_id = settings.who_client_id
        self.client_secret = settings.who_client_secret
        self.auth_url = settings.who_icd_auth_url
        self.scope = settings.who_icd_scope
        
        # Token storage
        self._access_token: Optional[str] = None
        self._token_expires_at: Optional[datetime] = None
        self._token_lock = asyncio.Lock()
    
    async def get_access_token(self) -> str:
        """
        Get a valid access token, refreshing if necessary
        
        Returns:
            str: Valid access token
            
        Raises:
            httpx.HTTPError: If authentication fails
        """
        async with self._token_lock:
            # Check if current token is still valid
            if self._is_token_valid():
                return self._access_token
            
            # Request new token
            return await self._request_new_token()
    
    def _is_token_valid(self) -> bool:
        """Check if current token is valid and not expired"""
        if not self._access_token or not self._token_expires_at:
            return False
        
        # Add 5 minute buffer before expiration
        buffer = timedelta(minutes=5)
        return datetime.now() < (self._token_expires_at - buffer)
    
    async def _request_new_token(self) -> str:
        """
        Request a new access token from WHO API
        
        Returns:
            str: New access token
            
        Raises:
            httpx.HTTPError: If authentication fails
        """
        logger.info("Requesting new WHO API access token")
        
        # Prepare OAuth2 client credentials request
        token_data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "client_credentials",
            "scope": self.scope
        }
        
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json"
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    self.auth_url,
                    data=token_data,
                    headers=headers
                )
                
                response.raise_for_status()
                token_response = response.json()
                
                # Extract token information
                self._access_token = token_response["access_token"]
                expires_in = token_response.get("expires_in", 3600)  # Default 1 hour
                
                # Calculate expiration time
                self._token_expires_at = datetime.now() + timedelta(seconds=expires_in)
                
                logger.info(f"Successfully obtained WHO API token, expires at {self._token_expires_at}")
                return self._access_token
                
        except httpx.HTTPError as e:
            logger.error(f"Failed to obtain WHO API token: {e}")
            if hasattr(e, 'response') and e.response:
                logger.error(f"Response content: {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error during WHO API authentication: {e}")
            raise
    
    async def get_authenticated_headers(self) -> Dict[str, str]:
        """
        Get headers with valid authentication for WHO API requests
        
        Returns:
            dict: Headers including Authorization bearer token
        """
        token = await self.get_access_token()
        
        return {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            "Accept-Language": "en",
            "API-Version": "v2"
        }
    
    def clear_token(self) -> None:
        """Clear stored token (useful for testing or forced refresh)"""
        self._access_token = None
        self._token_expires_at = None
        logger.info("WHO API token cleared")


# Global instance
who_auth_service = WHOAPIAuthService()