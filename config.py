from dotenv import load_dotenv
import os

load_dotenv()

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_DIR = os.path.join(BASE_DIR, 'database')

# database 폴더 생성 (없으면 만들기)
os.makedirs(DB_DIR, exist_ok=True)

class Config:
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(DB_DIR, 'interview.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY')
    KAKAO_CLIENT_ID = os.getenv('KAKAO_CLIENT_ID')
    KAKAO_CLIENT_SECRET = os.getenv('KAKAO_CLIENT_SECRET')
    KAKAO_REDIRECT_URI = os.getenv('KAKAO_REDIRECT_URI')
    FRONTEND_URL = os.getenv('FRONTEND_URL')
