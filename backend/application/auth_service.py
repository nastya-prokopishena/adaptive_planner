import bcrypt
from backend.infrastructure.db.repositories.user_repo import UserRepository

user_repo = UserRepository()

class AuthService:
    @staticmethod
    def hash_password(password: str) -> str:
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

    @staticmethod
    def check_password(password: str, hashed: str) -> bool:
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

    @staticmethod
    def register(email: str, password: str):
        if user_repo.get_by_email(email):
            return None, "Email already registered"
        password_hash = AuthService.hash_password(password)
        user = user_repo.create(email, password_hash)
        return user, None

    @staticmethod
    def login(email: str, password: str):
        user = user_repo.get_by_email(email)
        if not user or not user.password_hash:
            return None, "Invalid credentials"
        if not AuthService.check_password(password, user.password_hash):
            return None, "Invalid credentials"
        return user, None