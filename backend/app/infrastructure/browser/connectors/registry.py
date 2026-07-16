from app.application.ports.browser_automation import BrowserConnectorPort, BrowserConnectorRegistryPort
from app.infrastructure.browser.connectors.ats_connectors import (
    GreenhouseBrowserConnector,
    WorkdayBrowserConnector,
)
from app.infrastructure.browser.connectors.base import ConfigDrivenBrowserConnector, load_connector_config
from app.infrastructure.browser.connectors.job_bank_connector import JobBankCanadaBrowserConnector

SUPPORTED_CONNECTORS = (
    "job_bank_canada",
    "workpei",
    "indeed",
    "company_career_pages",
    "workday",
    "greenhouse",
)

_CUSTOM_CONNECTORS = {
    "job_bank_canada": JobBankCanadaBrowserConnector,
    "workday": WorkdayBrowserConnector,
    "greenhouse": GreenhouseBrowserConnector,
}


class BrowserConnectorRegistry(BrowserConnectorRegistryPort):
    """Resolves browser connectors by preset connector_key — not by URL."""

    def __init__(self):
        self._connectors: dict[str, BrowserConnectorPort] = {}
        for key in SUPPORTED_CONNECTORS:
            custom = _CUSTOM_CONNECTORS.get(key)
            if custom:
                self._connectors[key] = custom()
            else:
                self._connectors[key] = ConfigDrivenBrowserConnector(key, load_connector_config(key))

    def get(self, connector_key: str) -> BrowserConnectorPort:
        if connector_key not in self._connectors:
            raise ValueError(
                f"Unsupported browser connector: {connector_key}. "
                f"Supported: {', '.join(SUPPORTED_CONNECTORS)}"
            )
        return self._connectors[connector_key]

    def list_keys(self) -> list[str]:
        return list(self._connectors.keys())
