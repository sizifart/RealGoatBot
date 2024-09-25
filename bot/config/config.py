from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_ignore_empty=True)

    API_ID: int
    API_HASH: str
   
    REF_ID: str = "37d06dc8-fa31-4272-b9df-5f74d12cb6f8"
    USE_RANDOM_DELAY_IN_RUN: bool = True
    RANDOM_DELAY_IN_RUN: list[int] = [0, 15]
    FAKE_USERAGENT: bool = True
    SLEEP_TIME: list[int] = [1800, 3600]
    
    USE_PROXY_FROM_FILE: bool = False


settings = Settings()


