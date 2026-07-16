import inspect

from app.application.ports.future import (
    FutureBrowserAutomationPort,
    CompanyIntelligencePort,
    DesktopPackagingPort,
    InterviewCoachingPort,
    RecruiterCRMPort,
)


def test_browser_automation_port_is_abstract():
    assert inspect.isabstract(FutureBrowserAutomationPort)
    assert hasattr(FutureBrowserAutomationPort, "submit_application")
    assert hasattr(FutureBrowserAutomationPort, "pause_for_captcha")


def test_desktop_packaging_port_is_abstract():
    assert inspect.isabstract(DesktopPackagingPort)


def test_interview_coaching_port_is_abstract():
    assert inspect.isabstract(InterviewCoachingPort)


def test_company_intelligence_port_is_abstract():
    assert inspect.isabstract(CompanyIntelligencePort)


def test_recruiter_crm_port_is_abstract():
    assert inspect.isabstract(RecruiterCRMPort)
