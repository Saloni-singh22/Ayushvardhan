"""
Authentication middleware for ABHA OAuth 2.0 integration
Handles token validation and user authentication
"""

from fastapi import Request, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
import logging
from typing import Optional
import jwt
from datetime import datetime

from app.core.config import settings

logger = logging.getLogger(__name__)

security = HTTPBearer()


class AuthMiddleware(BaseHTTPMiddleware):
    """ABHA OAuth 2.0 authentication middleware"""
    
    # Routes that don't require authentication
    EXEMPT_ROUTES = {
        "/",
        "/health",
        "/docs",
        "/redoc", 
        "/openapi.json",
        "/fhir/metadata",
        "/api/v1/auth/abha/login",
        "/api/v1/auth/abha/callback",
        # Data processing endpoints for development/testing
        "/api/v1/data/upload",
        "/api/v1/data/validate", 
        "/api/v1/data/export",
        "/api/v1/data/template",
        # WHO ICD-11 TM2 endpoints - public access for integration testing
        "/api/v1/who-icd/health",
        "/api/v1/who-icd/search",
        "/api/v1/who-icd/entity",
        "/api/v1/who-icd/sync/tm2",
        "/api/v1/who-icd/search/keywords",
        "/api/v1/who-icd/codesystems",
        # NAMASTE-WHO mapping endpoints - public access for integration testing
        "/api/v1/mapping/create-comprehensive",
        "/api/v1/mapping/translate",
        "/api/v1/mapping/conceptmap",
        "/api/v1/mapping/status",
        # Enhanced multi-tier mapping endpoints - public access for testing
        "/api/v1/enhanced-mapping/create-multi-tier",
        "/api/v1/enhanced-mapping/status",
        "/api/v1/enhanced-mapping/analytics",
        "/api/v1/enhanced-mapping/tier-distribution",
        "/api/v1/enhanced-mapping/validate-mapping"
    }
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """Process request through authentication middleware"""
        
        # Skip authentication for exempt routes
        request_path = request.url.path
        
        # Check exact path matches
        if request_path in self.EXEMPT_ROUTES:
            return await call_next(request)
        
        # Check for WHO ICD route prefixes (to handle path parameters)
        if request_path.startswith("/api/v1/who-icd/"):
            return await call_next(request)
        
        # Check for mapping route prefixes (to handle path parameters)
        if request_path.startswith("/api/v1/mapping/"):
            return await call_next(request)
        
        # Check for enhanced mapping route prefixes (to handle path parameters)
        if request_path.startswith("/api/v1/enhanced-mapping/"):
            return await call_next(request)
        
        # Skip authentication for OPTIONS requests (CORS preflight)
        if request.method == "OPTIONS":
            return await call_next(request)
        
        # Extract authorization header
        authorization = request.headers.get("Authorization")
        
        if not authorization:
            if settings.debug:
                # In debug mode, allow requests without auth for development
                logger.warning(f"No authorization header for {request.url.path}")
                return await call_next(request)
            else:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authorization header required",
                    headers={"WWW-Authenticate": "Bearer"}
                )
        
        try:
            # Validate JWT token
            token = authorization.split(" ")[1] if " " in authorization else authorization
            user_info = await self.validate_jwt_token(token)
            
            # Add user info to request state
            request.state.user = user_info
            request.state.abha_number = user_info.get("abha_number")
            
            logger.info(f"Authenticated user: {user_info.get('abha_number')}")
            
        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            if settings.debug:
                # In debug mode, allow requests with invalid auth for development
                logger.warning("Debug mode: allowing request with invalid auth")
                request.state.user = {"abha_number": "debug_user", "debug": True}
                return await call_next(request)
            else:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid authentication credentials",
                    headers={"WWW-Authenticate": "Bearer"}
                )
        
        return await call_next(request)
    
    async def validate_jwt_token(self, token: str) -> dict:
        """Validate JWT token and extract user information"""
        try:
            # Decode JWT token
            payload = jwt.decode(
                token,
                settings.jwt_secret_key,
                algorithms=[settings.jwt_algorithm]
            )
            
            # Check token expiration
            exp = payload.get("exp")
            if exp and datetime.utcnow().timestamp() > exp:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token has expired"
                )
            
            # Extract user information
            abha_number = payload.get("sub")  # Subject should be ABHA number
            if not abha_number:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token: missing ABHA number"
                )
            
            # Validate ABHA number format (14 digits)
            if not abha_number.isdigit() or len(abha_number) != 14:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid ABHA number format"
                )
            
            return {
                "abha_number": abha_number,
                "token_type": payload.get("token_type", "access"),
                "scope": payload.get("scope", []),
                "iat": payload.get("iat"),
                "exp": payload.get("exp")
            }
            
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired"
            )
        except jwt.InvalidTokenError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid token: {str(e)}"
            )


async def get_current_user(request: Request) -> Optional[dict]:
    """Get current authenticated user from request state"""
    return getattr(request.state, "user", None)


async def get_current_abha_number(request: Request) -> Optional[str]:
    """Get current user's ABHA number from request state"""
    return getattr(request.state, "abha_number", None)


def require_auth(request: Request) -> dict:
    """Require authentication and return user info"""
    user = getattr(request.state, "user", None)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    return user