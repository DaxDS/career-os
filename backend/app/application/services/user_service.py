import uuid

from app.application.ports.audit import AuditPort
from app.application.ports.user_repository import UserRepositoryPort
from app.config import Settings
from app.domain.enums import AuditAction, AuditActor
from app.infrastructure.auth.jwt import (
    create_access_token,
    hash_password,
    verify_password,
)
from app.infrastructure.db.models import User, UserProfile
from app.infrastructure.logging.setup import get_logger

logger = get_logger(__name__)


class AuthService:
    def __init__(
        self,
        user_repo: UserRepositoryPort,
        settings: Settings,
        audit: AuditPort | None = None,
    ):
        self._user_repo = user_repo
        self._settings = settings
        self._audit = audit

    def register(self, email: str, password: str) -> tuple[User, str]:
        if self._settings.single_user_mode and self._user_repo.count_users() >= 1:
            raise ValueError("Single-user mode: account already exists")

        if self._user_repo.get_by_email(email):
            raise ValueError("Email already registered")

        user = User(
            email=email,
            hashed_password=hash_password(password),
        )
        user = self._user_repo.create_user(user)

        profile = UserProfile(
            user_id=user.id,
            legal_name=email.split("@")[0],
        )
        self._user_repo.create_profile(profile)

        token = create_access_token(user.id, self._settings)
        logger.info("user_registered", user_id=str(user.id), email=email)
        return user, token

    def login(self, email: str, password: str) -> tuple[User, str]:
        user = self._user_repo.get_by_email(email)
        if not user or not verify_password(password, user.hashed_password):
            raise ValueError("Invalid credentials")
        if not user.is_active:
            raise ValueError("Account is inactive")

        token = create_access_token(user.id, self._settings)
        logger.info("user_logged_in", user_id=str(user.id))
        return user, token

    def bootstrap_single_user(self) -> User | None:
        if not self._settings.single_user_mode:
            return None
        if self._user_repo.count_users() > 0:
            return None

        email = self._settings.default_user_email
        password = self._settings.default_user_password
        user, _ = self.register(email, password)
        logger.info("single_user_bootstrapped", email=email)
        if self._audit:
            self._audit.record(
                action=AuditAction.SYSTEM_EVENT,
                entity_type="user",
                entity_id=user.id,
                actor=AuditActor.SYSTEM,
                details={"event": "single_user_bootstrap", "email": email},
            )
        return user


class ProfileService:
    def __init__(self, user_repo: UserRepositoryPort, audit: AuditPort | None = None):
        self._user_repo = user_repo
        self._audit = audit

    def get_profile(self, user_id: uuid.UUID) -> UserProfile:
        profile = self._user_repo.get_profile(user_id)
        if not profile:
            raise ValueError("Profile not found")
        return profile

    def update_profile(self, user_id: uuid.UUID, data: dict) -> UserProfile:
        profile = self.get_profile(user_id)
        allowed = {
            "legal_name",
            "location_city",
            "location_province",
            "work_authorization",
            "immigration_goals",
            "preferred_provinces",
            "preferred_job_categories",
            "skills",
            "salary_min_cad",
            "salary_max_cad",
            "remote_preference",
            "languages",
            "phone",
            "linkedin_url",
        }
        for key, value in data.items():
            if key in allowed and value is not None:
                if key in ("work_authorization", "remote_preference"):
                    setattr(profile, key, value.value if hasattr(value, "value") else value)
                elif key == "preferred_job_categories":
                    setattr(
                        profile,
                        key,
                        [v.value if hasattr(v, "value") else v for v in value],
                    )
                else:
                    setattr(profile, key, value)

        profile = self._user_repo.update_profile(profile)
        if self._audit:
            self._audit.record(
                action=AuditAction.SYSTEM_EVENT,
                entity_type="user_profile",
                entity_id=profile.id,
                actor=AuditActor.USER,
                details={"event": "profile_updated", "fields": list(data.keys())},
            )
        return profile
