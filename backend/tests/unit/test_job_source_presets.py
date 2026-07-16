from app.domain.enums import JobSourcePreset, JobSourceType
from app.domain.job_source_presets import (
    JOB_SOURCE_PRESET_DEFINITIONS,
    get_preset_definition,
    is_reserved_source_name,
)


def test_all_five_presets_defined():
    assert len(JOB_SOURCE_PRESET_DEFINITIONS) == 5
    assert set(JOB_SOURCE_PRESET_DEFINITIONS) == set(JobSourcePreset)


def test_preset_names_match_user_requirements():
    names = {d.name for d in JOB_SOURCE_PRESET_DEFINITIONS.values()}
    assert names == {
        "Job Bank Canada",
        "WorkPEI",
        "Indeed",
        "Company Career Pages",
        "Manual URL Import",
    }


def test_preset_connector_keys_are_stable():
    live_search = {JobSourcePreset.JOB_BANK_CANADA, JobSourcePreset.INDEED}
    for preset, definition in JOB_SOURCE_PRESET_DEFINITIONS.items():
        assert definition.connector_key == preset.value
        expected = "active" if preset in live_search else "not_implemented"
        assert definition.config["connector_status"] == expected


def test_manual_url_import_is_manual_type():
    definition = JOB_SOURCE_PRESET_DEFINITIONS[JobSourcePreset.MANUAL_URL_IMPORT]
    assert definition.source_type == JobSourceType.MANUAL


def test_get_preset_definition_validates_key():
    definition = get_preset_definition("workpei")
    assert definition.name == "WorkPEI"


def test_reserved_source_names():
    assert is_reserved_source_name("Indeed")
    assert not is_reserved_source_name("My Custom Board")
