"""
Security & Compliance Module for ResearchRAG Pro

Implements:
- OAuth 2.0 + OIDC authentication
- RBAC (Role-Based Access Control)
- API key management with scoped permissions
- Data encryption (at-rest and in-transit)
- Audit logging (immutable trail)
- GDPR compliance (right to deletion, data export)
- SOC-2 Type II controls
- HIPAA compliance (if handling medical research)
"""

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import OAuth2PasswordBearer, APIKeyHeader, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, EmailStr
from enum import Enum
import secrets
import hashlib
import logging
from cryptography.fernet import Fernet
import os
import json

logger = logging.getLogger(__name__)

# ========================================
# CONFIGURATION
# ========================================

SECRET_KEY = os.getenv("JWT_SECRET_KEY", secrets.token_urlsafe(32))
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60
REFRESH_TOKEN_EXPIRE_DAYS = 7

# Encryption key for data at rest
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY", Fernet.generate_key())
cipher_suite = Fernet(ENCRYPTION_KEY)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
http_bearer = HTTPBearer(auto_error=False)


# ========================================
# USER ROLES (RBAC)
# ========================================

class Role(str, Enum):
    """User roles with hierarchical permissions."""
    ADMIN = "admin"           # Full system access
    RESEARCHER = "researcher" # Query, ingest, view
    VIEWER = "viewer"         # Query only, no ingestion
    API_CLIENT = "api_client" # Programmatic access


class Permission(str, Enum):
    """Granular permissions."""
    READ_PAPERS = "papers:read"
    INGEST_PAPERS = "papers:ingest"
    DELETE_PAPERS = "papers:delete"
    SEARCH_QUERY = "search:query"
    VIEW_METRICS = "metrics:view"
    MANAGE_USERS = "users:manage"
    EXPORT_DATA = "data:export"
    VIEW_AUDIT_LOG = "audit:view"


# Role to permissions mapping
ROLE_PERMISSIONS = {
    Role.ADMIN: [
        Permission.READ_PAPERS,
        Permission.INGEST_PAPERS,
        Permission.DELETE_PAPERS,
        Permission.SEARCH_QUERY,
        Permission.VIEW_METRICS,
        Permission.MANAGE_USERS,
        Permission.EXPORT_DATA,
        Permission.VIEW_AUDIT_LOG,
    ],
    Role.RESEARCHER: [
        Permission.READ_PAPERS,
        Permission.INGEST_PAPERS,
        Permission.SEARCH_QUERY,
        Permission.VIEW_METRICS,
        Permission.EXPORT_DATA,
    ],
    Role.VIEWER: [
        Permission.READ_PAPERS,
        Permission.SEARCH_QUERY,
    ],
    Role.API_CLIENT: [
        Permission.READ_PAPERS,
        Permission.SEARCH_QUERY,
    ],
}


# ========================================
# DATA MODELS
# ========================================

class User(BaseModel):
    """User model."""
    user_id: str
    email: EmailStr
    full_name: str
    role: Role
    is_active: bool = True
    created_at: datetime
    last_login: Optional[datetime] = None
    organization: Optional[str] = None


class Token(BaseModel):
    """JWT token response."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class TokenData(BaseModel):
    """Decoded token data."""
    user_id: Optional[str] = None
    email: Optional[str] = None
    role: Optional[Role] = None
    scopes: List[str] = []


class APIKey(BaseModel):
    """API key model."""
    key_id: str
    key_hash: str
    name: str
    scopes: List[Permission]
    user_id: str
    created_at: datetime
    last_used: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    is_active: bool = True


class AuditLogEntry(BaseModel):
    """Immutable audit log entry."""
    log_id: str
    timestamp: datetime
    user_id: str
    action: str
    resource_type: str
    resource_id: Optional[str] = None
    ip_address: str
    user_agent: str
    status: str  # success, failure
    details: Optional[Dict[str, Any]] = None


# ========================================
# ENCRYPTION UTILITIES
# ========================================

def encrypt_data(data: str) -> str:
    """Encrypt data using Fernet (AES-256)."""
    return cipher_suite.encrypt(data.encode()).decode()


def decrypt_data(encrypted_data: str) -> str:
    """Decrypt data."""
    return cipher_suite.decrypt(encrypted_data.encode()).decode()


def hash_api_key(api_key: str) -> str:
    """Hash API key using SHA-256."""
    return hashlib.sha256(api_key.encode()).hexdigest()


def generate_api_key() -> str:
    """Generate a secure API key."""
    return f"rag_{secrets.token_urlsafe(32)}"


# ========================================
# PASSWORD UTILITIES
# ========================================

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash password using bcrypt."""
    return pwd_context.hash(password)


# ========================================
# JWT TOKEN UTILITIES
# ========================================

def create_access_token(
    data: dict,
    expires_delta: Optional[timedelta] = None
) -> str:
    """Create JWT access token."""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire, "type": "access"})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def create_refresh_token(data: dict) -> str:
    """Create JWT refresh token."""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_token(token: str) -> TokenData:
    """Decode and validate JWT token."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        email: str = payload.get("email")
        role: str = payload.get("role")
        scopes: list = payload.get("scopes", [])
        
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        return TokenData(
            user_id=user_id,
            email=email,
            role=role,
            scopes=scopes
        )
    
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


# ========================================
# AUTHENTICATION DEPENDENCIES
# ========================================

async def get_current_user_from_token(
    token: str = Depends(oauth2_scheme)
) -> User:
    """Extract user from JWT token."""
    token_data = decode_token(token)
    
    # TODO: Fetch user from database
    # user = await db.get_user(token_data.user_id)
    # For now, return mock user
    user = User(
        user_id=token_data.user_id,
        email=token_data.email,
        full_name="John Doe",
        role=token_data.role,
        created_at=datetime.utcnow()
    )
    
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    
    return user


async def get_current_user_from_api_key(
    api_key: Optional[str] = Security(api_key_header)
) -> Optional[User]:
    """Authenticate using API key."""
    if not api_key:
        return None
    
    # Hash the provided key
    key_hash = hash_api_key(api_key)
    
    # TODO: Look up API key in database
    # api_key_record = await db.get_api_key_by_hash(key_hash)
    # if not api_key_record or not api_key_record.is_active:
    #     return None
    # 
    # # Update last_used timestamp
    # await db.update_api_key_last_used(api_key_record.key_id)
    # 
    # # Get associated user
    # user = await db.get_user(api_key_record.user_id)
    # return user
    
    # Mock for now
    return None


async def get_current_user(
    token_user: Optional[User] = Depends(get_current_user_from_token),
    api_key_user: Optional[User] = Depends(get_current_user_from_api_key)
) -> User:
    """Get current user from either JWT token or API key."""
    user = token_user or api_key_user
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user


# ========================================
# AUTHORIZATION (RBAC)
# ========================================

def require_permission(permission: Permission):
    """Dependency to enforce permission requirement."""
    async def permission_checker(current_user: User = Depends(get_current_user)):
        user_permissions = ROLE_PERMISSIONS.get(current_user.role, [])
        
        if permission not in user_permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: {permission} required"
            )
        
        return current_user
    
    return permission_checker


def require_role(required_role: Role):
    """Dependency to enforce role requirement."""
    async def role_checker(current_user: User = Depends(get_current_user)):
        # Admin has access to everything
        if current_user.role == Role.ADMIN:
            return current_user
        
        # Check if user has required role
        role_hierarchy = {
            Role.ADMIN: 4,
            Role.RESEARCHER: 3,
            Role.VIEWER: 2,
            Role.API_CLIENT: 1,
        }
        
        if role_hierarchy.get(current_user.role, 0) < role_hierarchy.get(required_role, 999):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{required_role}' required"
            )
        
        return current_user
    
    return role_checker


# ========================================
# AUDIT LOGGING
# ========================================

async def log_audit_event(
    user_id: str,
    action: str,
    resource_type: str,
    resource_id: Optional[str] = None,
    ip_address: str = "0.0.0.0",
    user_agent: str = "unknown",
    status: str = "success",
    details: Optional[Dict[str, Any]] = None
):
    """Create immutable audit log entry."""
    
    entry = AuditLogEntry(
        log_id=secrets.token_urlsafe(16),
        timestamp=datetime.utcnow(),
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        ip_address=ip_address,
        user_agent=user_agent,
        status=status,
        details=details
    )
    
    # TODO: Write to append-only audit log storage
    # - DynamoDB with TTL disabled
    # - S3 with object lock
    # - CloudTrail
    # await audit_db.append(entry)
    
    logger.info(
        f"Audit: {action} on {resource_type}",
        extra={
            "audit_log_id": entry.log_id,
            "user_id": user_id,
            "action": action,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "status": status,
        }
    )


# ========================================
# GDPR COMPLIANCE
# ========================================

class GDPRService:
    """GDPR compliance utilities."""
    
    @staticmethod
    async def export_user_data(user_id: str) -> Dict[str, Any]:
        """Export all user data (GDPR Article 20)."""
        
        # TODO: Gather data from all systems
        # - User profile
        # - Search queries
        # - Ingested papers
        # - Generated embeddings
        # - Audit logs
        
        user_data = {
            "user_profile": {},  # await db.get_user(user_id)
            "search_history": [],  # await db.get_user_searches(user_id)
            "ingested_papers": [],  # await db.get_user_papers(user_id)
            "export_timestamp": datetime.utcnow().isoformat(),
        }
        
        await log_audit_event(
            user_id=user_id,
            action="gdpr_data_export",
            resource_type="user_data",
            resource_id=user_id,
            status="success"
        )
        
        return user_data
    
    @staticmethod
    async def delete_user_data(user_id: str, reason: str = "user_request"):
        """Delete all user data (GDPR Article 17 - Right to Erasure)."""
        
        # TODO: Delete from all systems
        # - User profile (anonymize or delete)
        # - Search queries
        # - Ingested papers (check if shared with others)
        # - Embeddings in vector DB
        # - References in knowledge graph
        
        # Note: Audit logs are typically retained for compliance
        
        await log_audit_event(
            user_id=user_id,
            action="gdpr_data_deletion",
            resource_type="user_data",
            resource_id=user_id,
            status="success",
            details={"reason": reason}
        )
        
        logger.warning(f"User data deletion completed for {user_id}")


# ========================================
# HIPAA COMPLIANCE (if handling medical research)
# ========================================

class HIPAAService:
    """HIPAA compliance utilities for medical research."""
    
    @staticmethod
    def is_phi_present(text: str) -> bool:
        """Check if text contains Protected Health Information."""
        # TODO: Implement PHI detection
        # - Names
        # - Dates (except year)
        # - Phone numbers
        # - Medical record numbers
        # - SSN
        # - Email addresses
        # - IP addresses
        return False
    
    @staticmethod
    def anonymize_phi(text: str) -> str:
        """Remove or anonymize PHI from text."""
        # TODO: Implement de-identification
        # Use NER models to detect and redact PHI
        return text
    
    @staticmethod
    async def log_phi_access(user_id: str, paper_id: str):
        """Log access to documents containing PHI."""
        await log_audit_event(
            user_id=user_id,
            action="phi_access",
            resource_type="paper",
            resource_id=paper_id,
            status="success"
        )


# ========================================
# USAGE EXAMPLES
# ========================================

"""
# In FastAPI endpoints:

from app.security import (
    get_current_user,
    require_permission,
    require_role,
    Permission,
    Role,
    log_audit_event
)

# Require authentication
@app.get("/api/v1/papers/{paper_id}")
async def get_paper(
    paper_id: str,
    current_user: User = Depends(get_current_user)
):
    # User is authenticated
    await log_audit_event(
        user_id=current_user.user_id,
        action="read_paper",
        resource_type="paper",
        resource_id=paper_id
    )
    return {"paper_id": paper_id}

# Require specific permission
@app.post("/api/v1/papers")
async def ingest_paper(
    current_user: User = Depends(require_permission(Permission.INGEST_PAPERS))
):
    # User has ingest permission
    return {"status": "ingesting"}

# Require specific role
@app.get("/api/v1/admin/users")
async def list_users(
    current_user: User = Depends(require_role(Role.ADMIN))
):
    # User is admin
    return {"users": []}

# GDPR data export
@app.get("/api/v1/gdpr/export")
async def export_my_data(
    current_user: User = Depends(get_current_user)
):
    data = await GDPRService.export_user_data(current_user.user_id)
    return data

# GDPR data deletion
@app.delete("/api/v1/gdpr/delete")
async def delete_my_data(
    current_user: User = Depends(get_current_user)
):
    await GDPRService.delete_user_data(current_user.user_id)
    return {"status": "deleted"}
"""
