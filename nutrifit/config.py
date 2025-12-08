import os

from dotenv import load_dotenv

load_dotenv()



class BaseConfig:
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret")
    API_KEY = os.getenv("API_KEY", "dev-key")
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")


class DevConfig(BaseConfig):
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///nutrifit.db")


def get_config():
    return DevConfig
