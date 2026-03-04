"""Encryption utilities for storing sensitive data."""

import base64
from cryptography.fernet import Fernet

from app.config import settings


class EncryptionManager:
    """Manages encryption/decryption of sensitive fields."""

    def __init__(self):
        # Use ENCRYPTION_KEY from env, or generate a temporary one
        key = settings.encryption_key
        if not key:
            # For development, generate a key (not recommended for production)
            key = Fernet.generate_key().decode()
        self.cipher = Fernet(key.encode() if isinstance(key, str) else key)

    def encrypt(self, plaintext: str) -> str:
        """Encrypt a string and return base64-encoded ciphertext."""
        encrypted = self.cipher.encrypt(plaintext.encode())
        return base64.b64encode(encrypted).decode()

    def decrypt(self, ciphertext: str) -> str:
        """Decrypt a base64-encoded ciphertext and return plaintext."""
        decoded = base64.b64decode(ciphertext.encode())
        plaintext = self.cipher.decrypt(decoded)
        return plaintext.decode()


encryption_manager = EncryptionManager()
