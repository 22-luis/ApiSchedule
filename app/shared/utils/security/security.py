import bcrypt
from passlib.context import CryptContext

# Fix for passlib/bcrypt 4.0.0+ compatibility
# passlib expects bcrypt.__about__.__version__ which was removed in bcrypt 4.0.0
if not hasattr(bcrypt, "__about__"):
    bcrypt.__about__ = type('about', (object,), {'__version__': bcrypt.__version__})

from fastapi.security import HTTPBearer

oauth2_scheme = HTTPBearer()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str):
    return pwd_context.verify(plain_password, hashed_password)