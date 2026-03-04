from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    fudo_api_url: str = "https://api.fu.do"
    fudo_api_secret: str = ""
    database_url: str = ""
    frontend_url: str = "http://localhost:3000"
    admin_api_key: str = ""
    encryption_key: str = ""

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
