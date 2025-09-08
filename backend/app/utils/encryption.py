from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
import os
from typing import Dict, Any
import json
from ..core.config import settings

class EncryptionService:
    def __init__(self):
        # Generate key from the encryption key in settings
        if not settings.ENCRYPTION_KEY:
            raise ValueError("ENCRYPTION_KEY must be set in environment variables")
        
        password = settings.ENCRYPTION_KEY.encode()
        salt = b'salt_1234567890'  # In production, use a proper random salt per record
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password))
        self.cipher_suite = Fernet(key)
    
    def encrypt_credentials(self, credentials: Dict[str, Any]) -> str:
        """Encrypt database credentials"""
        credentials_json = json.dumps(credentials)
        encrypted_data = self.cipher_suite.encrypt(credentials_json.encode())
        return base64.urlsafe_b64encode(encrypted_data).decode()
    
    def decrypt_credentials(self, encrypted_credentials: str) -> Dict[str, Any]:
        """Decrypt database credentials"""
        encrypted_data = base64.urlsafe_b64decode(encrypted_credentials.encode())
        decrypted_data = self.cipher_suite.decrypt(encrypted_data)
        return json.loads(decrypted_data.decode())

# Global encryption service instance
encryption_service = EncryptionService()
