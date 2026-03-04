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

        # Fernet expects bytes. If key is a string, it should already be base64-encoded.
        # Pass directly - Fernet constructor handles both str and bytes.
        try:
            self.cipher = Fernet(key)
        except Exception as e:
            # Fallback for invalid key to prevent 500 crash
            # NOTE: This means encrypted data won't persist if the key is invalid
            import logging
            logging.error(f"ENCRYPTION_KEY is invalid or missing ({e}). Using temporary key.")
            self.cipher = Fernet(Fernet.generate_key())

    def encrypt(self, plaintext: str) -> str:
        """Encrypt a string and return base64-encoded ciphertext."""
        encrypted = self.cipher.encrypt(plaintext.encode())
        return base64.b64encode(encrypted).decode()

    def decrypt(self, ciphertext: str) -> str:
        """Decrypt a base64-encoded ciphertext and return plaintext."""
        decoded = base64.b64decode(ciphertext.encode())
        plaintext = self.cipher.decrypt(decoded)
        return plaintext.decode()


# Lazy initialization - prevent import errors if encryption key is invalid
_encryption_manager = None


def get_encryption_manager():
    global _encryption_manager
    if _encryption_manager is None:
        _encryption_manager = EncryptionManager()
    return _encryption_manager
