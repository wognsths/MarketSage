import json
import logging
import httpx
import jwt
from datetime import datetime, timedelta
from typing import Dict, Optional
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization

from app.common.types import TaskState

logger = logging.getLogger(__name__)

class PushNotificationSenderAuth:
    """Authentication utility for push notifications using JWT."""
    
    def __init__(self, expire_minutes: int = 60):
        """
        Initialize the auth provider.
        
        Args:
            expire_minutes: Token expiration time in minutes
        """
        self.private_key = None
        self.public_jwk = None
        self.expire_minutes = expire_minutes
    
    def generate_jwk(self) -> dict:
        """Generate a new RSA key pair and return the public JWK."""
        # Generate private key
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048
        )
        self.private_key = private_key
        
        # Export public key in JWK format
        public_key = private_key.public_key()
        numbers = public_key.public_numbers()
        
        # Convert to JWK format
        jwk = {
            "kty": "RSA",
            "n": self._int_to_base64url(numbers.n),
            "e": self._int_to_base64url(numbers.e),
            "alg": "RS256",
            "use": "sig",
            "kid": "marketsage-notification-key"
        }
        
        self.public_jwk = jwk
        return jwk
    
    def _int_to_base64url(self, value: int) -> str:
        """Convert an integer to base64url encoding."""
        import base64
        
        value_hex = format(value, 'x')
        if len(value_hex) % 2:
            value_hex = '0' + value_hex
            
        value_bytes = bytes.fromhex(value_hex)
        encoded = base64.urlsafe_b64encode(value_bytes).decode('ascii')
        return encoded.rstrip('=')
    
    def create_token(self, task_id: str, additional_claims: dict = None) -> str:
        """
        Create a JWT token for a task notification.
        
        Args:
            task_id: The ID of the task
            additional_claims: Additional claims to include in the token
            
        Returns:
            JWT token string
        """
        if not self.private_key:
            raise ValueError("Private key not generated. Call generate_jwk() first.")
        
        now = datetime.now()
        expires = now + timedelta(minutes=self.expire_minutes)
        
        claims = {
            "iss": "marketsage-host-agent",
            "sub": f"task:{task_id}",
            "iat": int(now.timestamp()),
            "exp": int(expires.timestamp()),
            "jti": f"{task_id}-{int(now.timestamp())}"
        }
        
        if additional_claims:
            claims.update(additional_claims)
        
        # Convert private key to PEM format for PyJWT
        pem = self.private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        
        # Create token
        token = jwt.encode(claims, pem, algorithm="RS256", headers={"kid": "marketsage-notification-key"})
        return token


class NotificationService:
    """Service for sending push notifications about task updates."""
    
    def __init__(self, sender_auth: PushNotificationSenderAuth):
        """
        Initialize the notification service.
        
        Args:
            sender_auth: Authentication provider for push notifications
        """
        self.sender_auth = sender_auth
        self.task_notification_urls = {}  # task_id → notification_url mapping
        self.client = httpx.AsyncClient(timeout=10.0)
        
    def register_task_notification(self, task_id: str, notification_url: str) -> None:
        """
        Register a task ID and notification URL mapping.
        
        Args:
            task_id: The ID of the task
            notification_url: URL to send notifications to
        """
        self.task_notification_urls[task_id] = notification_url
        logger.info(f"Registered notification URL for task {task_id}: {notification_url}")
        
    async def send_task_update(self, task_id: str, update_data: dict) -> bool:
        """
        Send a task update notification.
        
        Args:
            task_id: The ID of the task
            update_data: Update data to send
            
        Returns:
            True if notification was sent successfully, False otherwise
        """
        if task_id not in self.task_notification_urls:
            logger.warning(f"No notification URL registered for task {task_id}")
            return False
            
        notification_url = self.task_notification_urls[task_id]
        
        try:
            # Create authentication token
            token = self.sender_auth.create_token(task_id)
            
            # Send notification
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {token}"
            }
            
            response = await self.client.post(
                notification_url,
                json=update_data,
                headers=headers
            )
            
            if response.status_code >= 200 and response.status_code < 300:
                logger.info(f"Successfully sent notification for task {task_id}")
                return True
            else:
                logger.error(f"Failed to send notification for task {task_id}: {response.status_code} {response.text}")
                return False
                
        except Exception as e:
            logger.exception(f"Error sending notification for task {task_id}: {str(e)}")
            return False
    
    async def send_thought_process_update(self, task_id: str, thought_process: str) -> bool:
        """
        Send a thought process update notification.
        
        Args:
            task_id: The ID of the task
            thought_process: The agent's thought process text
            
        Returns:
            True if notification was sent successfully, False otherwise
        """
        update_data = {
            "type": "thought_process",
            "task_id": task_id,
            "thought_process": thought_process,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        return await self.send_task_update(task_id, update_data)
    
    async def send_agent_change_notification(self, task_id: str, agent_info: dict) -> bool:
        """
        Send an agent change notification.
        
        Args:
            task_id: The ID of the task
            agent_info: Information about the current active agent
            
        Returns:
            True if notification was sent successfully, False otherwise
        """
        update_data = {
            "type": "agent_change",
            "task_id": task_id,
            "agent": agent_info,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        return await self.send_task_update(task_id, update_data)
    
    async def send_task_completion_notification(self, task_id: str, result: dict) -> bool:
        """
        Send a task completion notification.
        
        Args:
            task_id: The ID of the task
            result: The final task result
            
        Returns:
            True if notification was sent successfully, False otherwise
        """
        update_data = {
            "type": "task_completion",
            "task_id": task_id,
            "result": result,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        return await self.send_task_update(task_id, update_data) 