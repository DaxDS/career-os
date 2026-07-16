from app.infrastructure.browser.connectors.registry import BrowserConnectorRegistry, SUPPORTED_CONNECTORS


def test_registry_lists_supported_connectors():
    registry = BrowserConnectorRegistry()
    assert set(registry.list_keys()) == set(SUPPORTED_CONNECTORS)


def test_registry_resolves_job_bank():
    registry = BrowserConnectorRegistry()
    connector = registry.get("job_bank_canada")
    assert connector.connector_key == "job_bank_canada"


def test_registry_resolves_workday():
    registry = BrowserConnectorRegistry()
    connector = registry.get("workday")
    assert connector.connector_key == "workday"


def test_registry_resolves_greenhouse():
    registry = BrowserConnectorRegistry()
    connector = registry.get("greenhouse")
    assert connector.connector_key == "greenhouse"
