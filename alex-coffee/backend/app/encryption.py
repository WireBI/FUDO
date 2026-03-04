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
            if isinstance(key, str):
                self.cipher = Fernet(key)
            else:
                self.cipher = Fernet(key)
        except ValueError as e:
            raise ValueError(
                f"Invalid ENCRYPTION_KEY environment variable: {e}. "
                "To generate a valid key, run:\n"
                "  python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\"\n"
                "Then set ENCRYPTION_KEY to the generated value in your Railway environment variables."
            )

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
