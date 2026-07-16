from pathlib import Path

from app.config import Settings, get_settings, resolve_paths
from app.infrastructure.db.models import AuditLog, PromptVersion, SystemMetadata


def test_settings_defaults():
    settings = Settings()
    assert settings.app_name == "Career OS"
    assert settings.single_user_mode is True
    assert settings.api_prefix == "/api/v1"


def test_settings_cached():
    s1 = get_settings()
    s2 = get_settings()
    assert s1 is s2


def test_resolve_paths_local(tmp_path):
    settings = Settings(storage_path=Path("storage"), prompts_path=Path("prompts"))
    resolved = resolve_paths(settings, tmp_path)
    assert resolved.storage_path == tmp_path / "storage"
    assert resolved.prompts_path == tmp_path / "prompts"


def test_foundation_table_names():
    assert SystemMetadata.__tablename__ == "system_metadata"
    assert AuditLog.__tablename__ == "audit_logs"
    assert PromptVersion.__tablename__ == "prompt_versions"
