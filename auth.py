import os
import json
from typing import Dict, Optional, Tuple
from datetime import datetime, timedelta
import secrets


class User:
    def __init__(self, username: str, email: str = "", full_name: str = ""):
        self.username = username
        self.email = email
        self.full_name = full_name
        self.created_at = datetime.utcnow()
        self.last_login = None

    def to_dict(self) -> Dict:
        return {
            "username": self.username,
            "email": self.email,
            "full_name": self.full_name,
            "created_at": self.created_at.isoformat(),
            "last_login": self.last_login.isoformat() if self.last_login else None
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "User":
        user = cls(
            username=data["username"],
            email=data.get("email", ""),
            full_name=data.get("full_name", "")
        )
        user.created_at = datetime.fromisoformat(data["created_at"])
        if data.get("last_login"):
            user.last_login = datetime.fromisoformat(data["last_login"])
        return user


class SimpleAuth:
    """Simple session-based auth — no passwords, just user existence check."""

    def __init__(self, users_file: str = "users.json"):
        self.users_file = users_file
        self.users: Dict[str, User] = {}
        self.sessions: Dict[str, Dict] = {}
        self.load_users()

    def load_users(self):
        if os.path.exists(self.users_file):
            try:
                with open(self.users_file) as f:
                    data = json.load(f)
                    for username, user_data in data.items():
                        self.users[username] = User.from_dict(user_data)
            except Exception as e:
                print(f"Warning: Could not load users file: {e}")

    def save_users(self):
        try:
            data = {u: self.users[u].to_dict() for u in self.users}
            with open(self.users_file, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Warning: Could not save users file: {e}")

    def create_user(self, username: str, email: str = "", full_name: str = "") -> bool:
        if username in self.users:
            return False
        self.users[username] = User(username, email, full_name)
        self.save_users()
        return True

    def get_user(self, username: str) -> Optional[User]:
        return self.users.get(username)

    def list_users(self) -> Dict[str, Dict]:
        return {u: self.users[u].to_dict() for u in self.users}

    def update_user(self, username: str, email: str = None, full_name: str = None) -> bool:
        if username not in self.users:
            return False
        user = self.users[username]
        if email is not None:
            user.email = email
        if full_name is not None:
            user.full_name = full_name
        self.save_users()
        return True

    def delete_user(self, username: str) -> bool:
        if username not in self.users:
            return False
        del self.users[username]
        self.save_users()
        return True

    def authenticate(self, username: str) -> Tuple[bool, Optional[str]]:
        if username not in self.users:
            return False, None

        self.users[username].last_login = datetime.utcnow()
        self.save_users()

        token = secrets.token_urlsafe(32)
        self.sessions[token] = {
            "username": username,
            "created_at": datetime.utcnow(),
            "expires_at": datetime.utcnow() + timedelta(hours=24)
        }
        return True, token

    def validate_session(self, session_token: str) -> Tuple[bool, Optional[str]]:
        if session_token not in self.sessions:
            return False, None

        session = self.sessions[session_token]
        if datetime.utcnow() > session["expires_at"]:
            del self.sessions[session_token]
            return False, None

        return True, session["username"]

    def logout(self, session_token: str) -> bool:
        if session_token in self.sessions:
            del self.sessions[session_token]
            return True
        return False


auth = SimpleAuth()


def require_auth(func):
    def wrapper(*args, **kwargs):
        session_token = kwargs.get("session_token")
        if not session_token:
            return {"error": "Authentication required"}
        valid, username = auth.validate_session(session_token)
        if not valid:
            return {"error": "Invalid or expired session"}
        kwargs["username"] = username
        return func(*args, **kwargs)
    return wrapper


if __name__ == "__main__":
    auth.create_user("john_doe", "john@example.com", "John Doe")

    success, token = auth.authenticate("john_doe")
    if success:
        print(f"Login successful, token: {token}")

        valid, username = auth.validate_session(token)
        if valid:
            print(f"Session valid for user: {username}")
            user = auth.get_user(username)
            print(f"User details: {user.to_dict()}")

        auth.logout(token)
        print("Logged out")
