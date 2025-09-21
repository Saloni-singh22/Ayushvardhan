"""
Audit middleware for India EHR Standards 2016 compliance
Tracks all API interactions for compliance and security monitoring
"""

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
import logging
import time
import json
from typing import Dict, Any
from datetime import datetime, timezone
import uuid

from app.core.config import settings

logger = logging.getLogger(__name__)


class AuditMiddleware(BaseHTTPMiddleware):
    """Audit trail middleware for India EHR Standards 2016 compliance"""
    
    def __init__(self, app):
        super().__init__(app)
        self.enabled = settings.audit_log_enabled
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """Process request through audit middleware"""
        
        if not self.enabled:
            return await call_next(request)
        
        # Generate unique request ID
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        # Capture request details
        start_time = time.time()
        request_data = await self.capture_request_data(request)
        
        # Process request
        response = await call_next(request)
        
        # Capture response details
        end_time = time.time()
        response_data = await self.capture_response_data(response, end_time - start_time)
        
        # Log audit trail
        await self.log_audit_trail(request, response, request_data, response_data, request_id)
        
        return response
    
    async def capture_request_data(self, request: Request) -> Dict[str, Any]:
        """Capture request data for audit logging"""
        try:
            # Get user information if available
            user_info = getattr(request.state, "user", {})
            abha_number = user_info.get("abha_number")
            
            # Capture request body for POST/PUT requests (with PII masking)
            body = None
            if request.method in ["POST", "PUT", "PATCH"]:
                try:
                    body_bytes = await request.body()
                    if body_bytes:
                        body = json.loads(body_bytes.decode())
                        body = self.mask_sensitive_data(body)
                except Exception:
                    body = "<unable_to_parse>"
            
            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "request_id": getattr(request.state, "request_id", None),
                "method": request.method,
                "url": str(request.url),
                "path": request.url.path,
                "query_params": dict(request.query_params),
                "headers": self.mask_sensitive_headers(dict(request.headers)),
                "body": body,
                "client_ip": self.get_client_ip(request),
                "user_agent": request.headers.get("user-agent"),
                "abha_number": abha_number,
                "content_type": request.headers.get("content-type"),
                "content_length": request.headers.get("content-length")
            }
        except Exception as e:
            logger.error(f"Error capturing request data: {e}")
            return {"error": "Failed to capture request data"}
    
    async def capture_response_data(self, response: Response, duration: float) -> Dict[str, Any]:
        """Capture response data for audit logging"""
        try:
            return {
                "status_code": response.status_code,
                "headers": self.mask_sensitive_headers(dict(response.headers)),
                "duration_ms": round(duration * 1000, 2),
                "content_type": response.headers.get("content-type"),
                "content_length": response.headers.get("content-length")
            }
        except Exception as e:
            logger.error(f"Error capturing response data: {e}")
            return {"error": "Failed to capture response data"}
    
    async def log_audit_trail(
        self, 
        request: Request, 
        response: Response, 
        request_data: Dict[str, Any], 
        response_data: Dict[str, Any],
        request_id: str
    ) -> None:
        """Log audit trail to database and/or file"""
        try:
            audit_record = {
                "id": request_id,
                "timestamp": datetime.now(timezone.utc),
                "event_type": "api_request",
                "action": f"{request.method} {request.url.path}",
                "resource_type": self.extract_resource_type(request.url.path),
                "user_id": request_data.get("abha_number"),
                "client_ip": request_data.get("client_ip"),
                "user_agent": request_data.get("user_agent"),
                "request": request_data,
                "response": response_data,
                "success": 200 <= response.status_code < 400,
                "consent_id": self.extract_consent_id(request),
                "session_id": self.extract_session_id(request),
                "compliance_flags": {
                    "india_ehr_2016": True,
                    "iso_22600": True,
                    "fhir_r4": self.is_fhir_request(request.url.path)
                }
            }
            
            # Log to structured logger
            if settings.audit_log_level == "DEBUG":
                logger.debug(f"Audit: {json.dumps(audit_record, default=str)}")
            else:
                logger.info(f"Audit: {request.method} {request.url.path} - {response.status_code}")
            
            # Store in database (async)
            await self.store_audit_record(audit_record)
            
        except Exception as e:
            logger.error(f"Error logging audit trail: {e}")
    
    async def store_audit_record(self, audit_record: Dict[str, Any]) -> None:
        """Store audit record in database"""
        try:
            from app.database import get_database
            db = await get_database()
            await db.audit_logs.insert_one(audit_record)
        except Exception as e:
            logger.error(f"Error storing audit record: {e}")
    
    def mask_sensitive_data(self, data: Any) -> Any:
        """Mask sensitive data in request/response bodies"""
        if isinstance(data, dict):
            masked_data = {}
            for key, value in data.items():
                if key.lower() in ["password", "token", "secret", "key", "authorization"]:
                    masked_data[key] = "***MASKED***"
                elif key.lower() in ["abha_number", "aadhaar", "mobile", "email"]:
                    masked_data[key] = self.mask_pii(str(value))
                else:
                    masked_data[key] = self.mask_sensitive_data(value)
            return masked_data
        elif isinstance(data, list):
            return [self.mask_sensitive_data(item) for item in data]
        else:
            return data
    
    def mask_sensitive_headers(self, headers: Dict[str, str]) -> Dict[str, str]:
        """Mask sensitive headers"""
        masked_headers = {}
        for key, value in headers.items():
            if key.lower() in ["authorization", "x-api-key", "x-auth-token"]:
                masked_headers[key] = "***MASKED***"
            else:
                masked_headers[key] = value
        return masked_headers
    
    def mask_pii(self, value: str) -> str:
        """Mask personally identifiable information"""
        if len(value) <= 4:
            return "***"
        return value[:2] + "*" * (len(value) - 4) + value[-2:]
    
    def get_client_ip(self, request: Request) -> str:
        """Extract client IP address"""
        # Check for forwarded headers first
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip
        
        # Fallback to direct client IP
        return getattr(request.client, "host", "unknown")
    
    def extract_resource_type(self, path: str) -> str:
        """Extract FHIR resource type from path"""
        if "/fhir/" in path:
            parts = path.split("/fhir/")
            if len(parts) > 1:
                resource_parts = parts[1].split("/")
                if resource_parts:
                    return resource_parts[0]
        elif "/api/v1/" in path:
            parts = path.split("/api/v1/")
            if len(parts) > 1:
                api_parts = parts[1].split("/")
                if api_parts:
                    return api_parts[0]
        return "unknown"
    
    def extract_consent_id(self, request: Request) -> str:
        """Extract consent ID from request"""
        # Check headers
        consent_id = request.headers.get("x-consent-id")
        if consent_id:
            return consent_id
        
        # Check query parameters
        return request.query_params.get("consent_id", "")
    
    def extract_session_id(self, request: Request) -> str:
        """Extract session ID from request"""
        return request.headers.get("x-session-id", "")
    
    def is_fhir_request(self, path: str) -> bool:
        """Check if request is FHIR-related"""
        return "/fhir/" in path or any(
            resource in path for resource in 
            ["CodeSystem", "ConceptMap", "ValueSet", "Bundle"]
        )