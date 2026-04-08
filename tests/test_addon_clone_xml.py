"""
Tests for resources/addon_clone.xml; the template used to generate clone addons.

The clone template MUST declare every Python module dependency that the clone's
runtime code paths use. Kodi sets up sys.path for a script addon based on its
declared <import> entries, so a missing dependency results in ImportError at
runtime.
"""
import os
from xml.etree import ElementTree as et


REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
CLONE_TEMPLATE = os.path.join(REPO_ROOT, 'resources', 'addon_clone.xml')
MAIN_ADDON_XML = os.path.join(REPO_ROOT, 'addon.xml')


def _get_imports(addon_xml_path):
    """Return a dict of {addon_id: version} for all <import> entries."""
    tree = et.parse(addon_xml_path)
    root = tree.getroot()
    requires = root.find('requires')
    if requires is None:
        return {}
    return {
        imp.get('addon'): imp.get('version')
        for imp in requires.findall('import')
    }


class TestCloneTemplateDependencies:
    """Regression tests for clone addon.xml requires section."""

    def test_clone_template_exists(self):
        assert os.path.isfile(CLONE_TEMPLATE), (
            f"Clone template missing: {CLONE_TEMPLATE}"
        )

    def test_clone_declares_xbmc_python(self):
        """Every Kodi script addon needs xbmc.python."""
        imports = _get_imports(CLONE_TEMPLATE)
        assert 'xbmc.python' in imports

    def test_clone_declares_pymysql_for_shared_db_sync(self):
        """
        Regression for 2026-04-07 RCA.

        Clones perform shared DB read-only sync (added in alpha2). The sync
        path imports pymysql via shared_db.SharedDatabase._connect(). Without
        this declaration, Kodi does not add script.module.pymysql to the
        clone's sys.path and the import raises ImportError, breaking sync.
        """
        imports = _get_imports(CLONE_TEMPLATE)
        assert 'script.module.pymysql' in imports, (
            "Clone template must declare script.module.pymysql so that "
            "Kodi adds it to the clone's sys.path. Without this, clones "
            "cannot import pymysql and shared DB sync silently breaks."
        )

    def test_clone_pymysql_version_matches_main_addon(self):
        """
        Clone and main must request the same pymysql version to avoid
        Kodi resolving to different copies.
        """
        clone_imports = _get_imports(CLONE_TEMPLATE)
        main_imports = _get_imports(MAIN_ADDON_XML)
        assert main_imports.get('script.module.pymysql') is not None, (
            "Main addon.xml must declare script.module.pymysql"
        )
        assert clone_imports.get('script.module.pymysql') == main_imports.get('script.module.pymysql'), (
            "Clone and main must request matching pymysql versions"
        )
