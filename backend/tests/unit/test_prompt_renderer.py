from app.infrastructure.prompts.renderer import PromptRenderer


def test_renders_simple_variables():
    renderer = PromptRenderer()
    result = renderer.render("Title: {{job_title}}\nCompany: {{company}}", {
        "job_title": "Developer",
        "company": "Acme",
    })
    assert "Title: Developer" in result
    assert "Company: Acme" in result


def test_missing_variable_becomes_empty():
    renderer = PromptRenderer()
    result = renderer.render("{{missing}}", {})
    assert result == ""
