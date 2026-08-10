"""Tests for addon.xml metadata constraints.

These guard the limits that kodi-addon-checker enforces via the Kodi metadata
schema, so a violation fails at commit time instead of in CI after a release
has already been tagged and published.

Logging: none. Pure static checks against the packaged addon.xml.
"""
import os
from xml.etree import ElementTree as ET

import pytest

# xml_schema/matrix_metadata.xsd caps <news> via the nonEmptyStringCapped
# simple type: <xs:maxLength value="1500"/>. Kodi truncates longer text and
# kodi-addon-checker reports it as a PROBLEM, which fails the build.
NEWS_MAX_LENGTH = 1500

ADDON_XML = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'addon.xml')


@pytest.fixture(scope='module')
def addon_root():
    """Parsed root element of the shipped addon.xml."""
    return ET.parse(ADDON_XML).getroot()


def test_addon_xml_parses(addon_root):
    """addon.xml must be well-formed XML with the expected addon id."""
    assert addon_root.tag == 'addon'
    assert addon_root.get('id') == 'script.easytv'


def test_news_within_schema_length_limit(addon_root):
    """<news> must stay within the schema cap.

    Regression test ported from EasyMovie, where v1.3.4 pushed the element
    to 1666 characters and kodi-addon-checker rejected it with "value length
    cannot be greater than 1500". Trim the oldest version block when adding
    a new one.
    """
    news_elements = addon_root.findall('.//news')
    assert len(news_elements) == 1, "addon.xml should declare exactly one <news> element"

    news = news_elements[0].text or ''
    assert len(news) <= NEWS_MAX_LENGTH, (
        "<news> is {0} characters, over the {1} character schema cap by {2}. "
        "Remove the oldest version block.".format(len(news), NEWS_MAX_LENGTH, len(news) - NEWS_MAX_LENGTH)
    )


def test_news_starts_with_current_version(addon_root):
    """The newest <news> block must describe the version being shipped."""
    version = addon_root.get('version')
    news = (addon_root.findall('.//news')[0].text or '').strip()
    assert news.startswith("v{0} ".format(version)), (
        "<news> should lead with the current version v{0}".format(version)
    )
