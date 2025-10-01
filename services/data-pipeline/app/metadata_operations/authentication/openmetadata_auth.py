"""
OpenMetadata authentication implementation
"""

import logging
import base64
import requests
import os
from typing import Dict, Optional
from datetime import datetime, timedelta
from .auth_interface import AuthenticationInterface
from ..models import AuthenticationResult, AuthenticationType

logger = logging.getLogger(__name__)


class OpenMetadataAuth(AuthenticationInterface):
    """OpenMetadata authentication provider"""
    
    def __init__(self, host: str, port: str, admin_email: str):
        """
        Initialize OpenMetadata authentication
        
        Args:
            host: OpenMetadata server host
            port: OpenMetadata server port
            admin_email: Admin email for authentication
        """
        self.host = host
        self.port = port
        self.admin_email = admin_email
        self.auth_token: Optional[str] = None
        self.token_expires_at: Optional[datetime] = None
        self.base_url = f"http://{host}:{port}/api"
        
        # Check for JWT token in environment
        self.jwt_token = os.getenv("OPENMETADATA_JWT_TOKEN")
        self.auth_provider = os.getenv("OPENMETADATA_AUTH_PROVIDER", "basic").lower()
    
    @property
    def auth_type(self) -> AuthenticationType:
        """Get the authentication type"""
        return AuthenticationType.JWT if self.auth_token and not self.auth_token.startswith('Basic ') else AuthenticationType.BASIC
    
    async def authenticate(self) -> AuthenticationResult:
        """
        Authenticate with OpenMetadata using JWT token for ingestion-bot
        
        Returns:
            Authentication result
        """
        try:
            logger.info("🔑 Attempting to authenticate with OpenMetadata...")
            
            # Method 1: Use JWT token from environment if available
            if self.jwt_token and self.auth_provider == "jwt":
                jwt_result = await self._authenticate_with_provided_jwt()
                if jwt_result.success:
                    return jwt_result
            
            # Method 2: Try ingestion-bot basic auth directly
            ingestion_result = await self._authenticate_with_ingestion_bot()
            if ingestion_result.success:
                return ingestion_result
            
            # Method 3: Try to get JWT token for ingestion-bot
            jwt_result = await self._authenticate_with_jwt()
            if jwt_result.success:
                return jwt_result
            
            # Method 4: Fallback to basic auth for admin
            basic_result = await self._authenticate_with_basic()
            if basic_result.success:
                return basic_result
            
            # If all methods fail
            logger.warning("❌ All authentication methods failed")
            return AuthenticationResult(
                success=False,
                auth_type=AuthenticationType.NO_AUTH,
                error_message="All authentication methods failed"
            )
            
        except Exception as e:
            logger.error(f"Authentication attempt failed: {e}")
            return AuthenticationResult(
                success=False,
                auth_type=AuthenticationType.NO_AUTH,
                error_message=str(e)
            )
    
    async def _authenticate_with_provided_jwt(self) -> AuthenticationResult:
        """Authenticate using provided JWT token from environment"""
        try:
            logger.info("🎯 Using provided JWT token for authentication...")
            
            # Test the JWT token
            test_headers = {
                'Authorization': f'Bearer {self.jwt_token}',
                'Content-Type': 'application/json'
            }
            
            # Test with database services endpoint
            test_response = requests.get(
                f"{self.base_url}/v1/services/databaseServices",
                headers=test_headers,
                timeout=10
            )
            
            if test_response.status_code == 200:
                self.auth_token = self.jwt_token
                logger.info("✅ JWT token authentication successful!")
                return AuthenticationResult(
                    success=True,
                    auth_type=AuthenticationType.JWT,
                    token=self.jwt_token
                )
            else:
                logger.warning(f"JWT token test failed: {test_response.status_code} - {test_response.text[:200]}")
                return AuthenticationResult(
                    success=False,
                    auth_type=AuthenticationType.JWT,
                    error_message=f"JWT token validation failed: {test_response.status_code}"
                )
                
        except Exception as e:
            logger.error(f"JWT token authentication failed: {e}")
            return AuthenticationResult(
                success=False,
                auth_type=AuthenticationType.JWT,
                error_message=str(e)
            )

    async def _authenticate_with_ingestion_bot(self) -> AuthenticationResult:
        """Authenticate directly with ingestion-bot credentials"""
        try:
            logger.info("🤖 Attempting direct ingestion-bot authentication...")
            
            # Try different ingestion-bot credentials
            credentials_to_try = [
                "ingestion-bot@open-metadata.org:ingestion-bot",
                "ingestion-bot@open-metadata.org:admin", 
                "ingestion-bot@open-metadata.org:",
            ]
            
            for creds in credentials_to_try:
                bot_b64 = base64.b64encode(creds.encode()).decode()
                
                # Test with version endpoint first
                test_response = requests.get(
                    f"{self.base_url}/v1/system/version",
                    headers={'Authorization': f'Basic {bot_b64}'},
                    timeout=10
                )
                
                if test_response.status_code == 200:
                    # Test with database services endpoint
                    api_test_response = requests.get(
                        f"{self.base_url}/v1/services/databaseServices",
                        headers={'Authorization': f'Basic {bot_b64}'},
                        timeout=10
                    )
                    
                    if api_test_response.status_code == 200:
                        self.auth_token = f"Basic {bot_b64}"
                        logger.info(f"✅ Ingestion-bot basic auth successful with: {creds.split(':')[0]}")
                        return AuthenticationResult(
                            success=True,
                            auth_type=AuthenticationType.BASIC,
                            token=self.auth_token
                        )
                    else:
                        logger.debug(f"API test failed for ingestion-bot - Status: {api_test_response.status_code}")
                else:
                    logger.debug(f"Version test failed for ingestion-bot - Status: {test_response.status_code}")
            
            return AuthenticationResult(
                success=False,
                auth_type=AuthenticationType.BASIC,
                error_message="Ingestion-bot basic authentication failed"
            )
            
        except Exception as e:
            logger.debug(f"Ingestion-bot auth failed: {e}")
            return AuthenticationResult(
                success=False,
                auth_type=AuthenticationType.BASIC,
                error_message=str(e)
            )

    async def _authenticate_with_jwt(self) -> AuthenticationResult:
        """Authenticate using JWT token for ingestion-bot"""
        try:
            logger.info("🔑 Attempting JWT authentication with ingestion-bot...")
            
            # First, try to authenticate as admin to create/access the bot
            admin_credentials = "admin@open-metadata.org:admin"
            admin_b64 = base64.b64encode(admin_credentials.encode()).decode()
            admin_headers = {
                'Authorization': f'Basic {admin_b64}',
                'Content-Type': 'application/json'
            }
            
            # Test admin access first
            admin_test = requests.get(f"{self.base_url}/v1/system/version", headers=admin_headers, timeout=10)
            if admin_test.status_code != 200:
                logger.warning(f"Admin access test failed: {admin_test.status_code}")
                return AuthenticationResult(
                    success=False,
                    auth_type=AuthenticationType.JWT,
                    error_message=f"Admin access failed: {admin_test.status_code}"
                )
            
            # Check if ingestion-bot exists
            bot_url = f"{self.base_url}/v1/bots/name/ingestion-bot"
            bot_response = requests.get(bot_url, headers=admin_headers, timeout=10)
            
            if bot_response.status_code == 200:
                bot_data = bot_response.json()
                logger.info("✅ Found existing ingestion-bot account")
                
                # Get the bot's user ID
                bot_user_id = bot_data.get('botUser', {}).get('id') if isinstance(bot_data.get('botUser'), dict) else None
                if not bot_user_id:
                    logger.warning("Bot user ID not found in bot data")
                    return AuthenticationResult(
                        success=False,
                        auth_type=AuthenticationType.JWT,
                        error_message="Bot user ID not found"
                    )
                
                # Generate JWT token for the bot user
                jwt_token = await self._generate_jwt_token(bot_user_id, admin_headers)
                if jwt_token:
                    self.auth_token = jwt_token
                    self.token_expires_at = datetime.now() + timedelta(days=365)  # Long-lived token
                    logger.info("✅ Successfully generated JWT token for ingestion-bot")
                    return AuthenticationResult(
                        success=True,
                        auth_type=AuthenticationType.JWT,
                        token=jwt_token,
                        expires_at=self.token_expires_at
                    )
                        
            elif bot_response.status_code == 404:
                logger.info("ℹ️ ingestion-bot not found, trying to create it...")
                
                # Create ingestion-bot
                if await self._create_ingestion_bot(admin_headers):
                    # Recursively try authentication again
                    return await self._authenticate_with_jwt()
            else:
                logger.warning(f"Unexpected response when checking for ingestion-bot: {bot_response.status_code}")
            
            return AuthenticationResult(
                success=False,
                auth_type=AuthenticationType.JWT,
                error_message="Failed to authenticate with JWT"
            )
            
        except Exception as e:
            logger.error(f"JWT authentication failed: {e}")
            return AuthenticationResult(
                success=False,
                auth_type=AuthenticationType.JWT,
                error_message=str(e)
            )
    
    async def _authenticate_with_basic(self) -> AuthenticationResult:
        """Authenticate using basic auth for admin"""
        try:
            # Try different admin credentials
            credentials_to_try = [
                "admin@open-metadata.org:admin",  # Admin email with admin password
                "admin:admin",  # Admin username with admin password
                f"{self.admin_email}:admin",  # Configured email with admin password
                "admin:",  # Standard admin with empty password
                f"{self.admin_email}:",  # Email with empty password
            ]
            
            for creds in credentials_to_try:
                admin_b64 = base64.b64encode(creds.encode()).decode()
                
                # Test with a more permissive endpoint first
                test_response = requests.get(
                    f"{self.base_url}/v1/system/version",
                    headers={'Authorization': f'Basic {admin_b64}'},
                    timeout=10
                )
                
                if test_response.status_code == 200:
                    # Now test with an actual API endpoint that requires auth
                    api_test_response = requests.get(
                        f"{self.base_url}/v1/services/databaseServices",
                        headers={'Authorization': f'Basic {admin_b64}'},
                        timeout=10
                    )
                    
                    if api_test_response.status_code == 200:
                        self.auth_token = f"Basic {admin_b64}"
                        logger.info(f"✅ Using Basic Auth with credentials: {creds.split(':')[0]}:***")
                        return AuthenticationResult(
                            success=True,
                            auth_type=AuthenticationType.BASIC,
                            token=self.auth_token
                        )
                    else:
                        logger.debug(f"API test failed for {creds.split(':')[0]} - Status: {api_test_response.status_code}")
                else:
                    logger.debug(f"Version test failed for {creds.split(':')[0]} - Status: {test_response.status_code}")
            
            # If all credentials fail, try no-auth approach (for development setups)
            no_auth_response = requests.get(
                f"{self.base_url}/v1/services/databaseServices",
                headers={'Content-Type': 'application/json'},
                timeout=10
            )
            
            if no_auth_response.status_code == 200:
                self.auth_token = None  # No auth needed
                logger.info("✅ Using No Auth (development mode)")
                return AuthenticationResult(
                    success=True,
                    auth_type=AuthenticationType.BASIC,
                    token=""
                )
            
            return AuthenticationResult(
                success=False,
                auth_type=AuthenticationType.BASIC,
                error_message=f"All authentication methods failed. Last status: {no_auth_response.status_code}"
            )
            
        except Exception as e:
            logger.debug(f"Basic auth failed: {e}")
            return AuthenticationResult(
                success=False,
                auth_type=AuthenticationType.BASIC,
                error_message=str(e)
            )
    
    async def _generate_jwt_token(self, user_id: str, admin_headers: Dict[str, str]) -> Optional[str]:
        """Generate JWT token for user/bot"""
        try:
            logger.info(f"🔑 Generating JWT token for user ID: {user_id}")
            
            # Method 1: Try the auth-mechanism endpoint
            token_url = f"{self.base_url}/v1/users/auth-mechanism"
            token_data = {
                "authType": "JWT",
                "config": {
                    "JWTTokenExpiry": "Unlimited"
                }
            }
            
            token_response = requests.put(
                f"{token_url}/{user_id}", 
                json=token_data, 
                headers=admin_headers, 
                timeout=10
            )
            
            logger.info(f"Auth mechanism response: {token_response.status_code}")
            if token_response.status_code in [200, 201]:
                token_result = token_response.json()
                jwt_token = token_result.get('config', {}).get('JWTToken')
                if jwt_token:
                    logger.info("✅ JWT token generated successfully via auth-mechanism")
                    return jwt_token
                else:
                    logger.warning("JWT token not found in auth-mechanism response")
            else:
                logger.warning(f"Auth mechanism failed: {token_response.status_code} - {token_response.text}")
            
            # Method 2: Try the generateToken endpoint
            generate_url = f"{self.base_url}/v1/users/generateToken"
            generate_data = {
                "userId": user_id,
                "JWTTokenExpiry": "Unlimited"
            }
            
            generate_response = requests.post(
                generate_url,
                json=generate_data,
                headers=admin_headers,
                timeout=10
            )
            
            logger.info(f"Generate token response: {generate_response.status_code}")
            if generate_response.status_code in [200, 201]:
                generate_result = generate_response.json()
                jwt_token = generate_result.get('JWTToken') or generate_result.get('token')
                if jwt_token:
                    logger.info("✅ JWT token generated successfully via generateToken")
                    return jwt_token
                else:
                    logger.warning("JWT token not found in generateToken response")
            else:
                logger.warning(f"Generate token failed: {generate_response.status_code} - {generate_response.text}")
            
            return None
            
        except Exception as e:
            logger.error(f"JWT token generation failed: {e}")
            return None
    
    async def _create_ingestion_bot(self, admin_headers: Dict[str, str]) -> bool:
        """Create ingestion-bot if it doesn't exist"""
        try:
            logger.info("🤖 Creating ingestion-bot account for JWT authentication...")
            
            # First, create the bot user
            bot_user_data = {
                "name": "ingestion-bot",
                "displayName": "Ingestion Bot User",
                "email": "ingestion-bot@open-metadata.org",
                "isBot": True,
                "profile": {
                    "images": {
                        "image": "",
                        "image24": "",
                        "image32": "",
                        "image48": "",
                        "image72": "",
                        "image192": "",
                        "image512": ""
                    }
                }
            }
            
            user_response = requests.post(
                f"{self.base_url}/v1/users",
                json=bot_user_data,
                headers=admin_headers,
                timeout=30
            )
            
            if user_response.status_code not in [200, 201]:
                logger.warning(f"Failed to create bot user: {user_response.status_code} - {user_response.text}")
                # Check if user already exists
                if "already exists" in user_response.text.lower():
                    logger.info("Bot user already exists, continuing...")
                else:
                    return False
            else:
                logger.info("✅ Created bot user successfully")
            
            # Now create the bot entity
            create_bot_data = {
                "name": "ingestion-bot",
                "displayName": "Ingestion Bot",
                "description": "Bot account for metadata ingestion with JWT authentication",
                "botUser": "ingestion-bot@open-metadata.org"
            }
            
            create_response = requests.post(
                f"{self.base_url}/v1/bots",
                json=create_bot_data,
                headers=admin_headers,
                timeout=30
            )
            
            if create_response.status_code in [200, 201]:
                logger.info("✅ Created ingestion-bot successfully")
                return True
            else:
                logger.warning(f"Failed to create ingestion-bot: {create_response.status_code} - {create_response.text}")
                # Check if bot already exists
                if "already exists" in create_response.text.lower():
                    logger.info("Ingestion-bot already exists, continuing...")
                    return True
                return False
            
        except Exception as e:
            logger.error(f"Failed to create ingestion-bot: {e}")
            return False
    
    def get_auth_headers(self) -> Dict[str, str]:
        """Get authentication headers for API requests"""
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        
        if self.auth_token:
            if self.auth_token.startswith('Basic '):
                headers['Authorization'] = self.auth_token
            elif self.auth_token:  # JWT or other token
                headers['Authorization'] = f'Bearer {self.auth_token}'
        # If auth_token is None or empty, don't add Authorization header (no-auth mode)
        
        return headers
    
    async def refresh_token(self) -> AuthenticationResult:
        """Refresh the authentication token"""
        # For OpenMetadata, we re-authenticate
        return await self.authenticate()
    
    def is_token_valid(self) -> bool:
        """Check if current token is valid"""
        if not self.auth_token:
            return False
        
        if self.token_expires_at:
            return datetime.now() < self.token_expires_at
        
        # For basic auth tokens, assume they're always valid
        return True
