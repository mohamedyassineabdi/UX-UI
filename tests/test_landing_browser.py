"""The landing page publishes valid JSON-LD for search engines in both languages. Run npm run build first."""
import json

import pytest
from playwright.sync_api import expect

from test_frontend_browser import browser, ui  # noqa: F401
from test_server_security import api_server  # noqa: F401


@pytest.mark.parametrize("query, lang", [("", "en"), ("?lang=fr", "fr")])
def test_landing_structured_data_is_valid_json_ld(ui, query, lang):
    page, instance, _ = ui
    page.goto(f"http://127.0.0.1:{instance.server_port}/{query}")
    script = page.locator('script[type="application/ld+json"]')
    expect(script).to_have_count(1)
    data = json.loads(script.text_content())
    assert data["@type"] == "SoftwareApplication" and data["inLanguage"] == lang
    assert len(data["featureList"]) == 7
