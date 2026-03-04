from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    fudo_api_url: str = "https://api.fu.do"
    fudo_api_id: str = ""
    fudo_api_secret: str = ""
    database_url: str = ""
    frontend_url: str = "http://localhost:3000"
    admin_api_key: str = ""
    encryption_key: str = ""

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()

# Helper for users to generate a valid encryption key
def generate_encryption_key() -> str:
    """Generate a valid Fernet encryption key for use in ENCRYPTION_KEY environment variable."""
    from cryptography.fernet import Fernet
    return Fernet.generate_key().decode()
