\"\"\"Security utilities.\"\"\"
from passlib.context import CryptContext
from datetime import datetime, timedelta
import jwt

SECRET_KEY = "SUPER_SECRET_KEY_CHANGE_ME_IN_PROD"
ALGORITHM = "HS256"

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(subject: str, expires_delta: timedelta):
    expire = datetime.utcnow() + expires_delta
    to_encode = {"exp": expire, "sub": str(subject)}
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
