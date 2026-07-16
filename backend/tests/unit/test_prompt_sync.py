import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import Settings
from app.infrastructure.db.base import Base
from app.infrastructure.prompts.registry import PromptRegistry
from app.infrastructure.prompts.sync import PromptSyncService


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def registry(db_session, tmp_path):
    prompts_dir = tmp_path / "prompts"
    prompts_dir.mkdir()
    manifest = """
prompts:
  resume_selection:
    file: resume_selection.md
    capability: resume_selection
"""
    (prompts_dir / "manifest.yaml").write_text(manifest)
    (prompts_dir / "resume_selection.md").write_text("# Resume Selection\n{{job_title}}")
    settings = Settings(storage_path=tmp_path / "storage", prompts_path=prompts_dir)
    return PromptRegistry(settings, db_session)


def test_sync_all_registers_prompts(registry):
    result = PromptSyncService(registry).sync_all()
    assert result["synced"] == 1
    assert result["errors"] == []
    active = registry.get_active_version("resume_selection")
    assert active is not None
    assert registry.get_active_content("resume_selection").startswith("# Resume Selection")


def test_sync_is_idempotent(registry):
    service = PromptSyncService(registry)
    first = service.sync_all()
    second = service.sync_all()
    assert first["synced"] == 1
    assert second["unchanged"] == 1
