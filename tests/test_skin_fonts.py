"""Tests for skin-adaptive font mapping."""
import os
import time

import pytest

import resources.lib.ui.skin_fonts as sf
from resources.lib.ui.skin_fonts import (
    ANCHOR_SIZES,
    build_font_map,
    cache_key,
    parse_fontset,
    substitute_fonts,
)


@pytest.fixture(autouse=True)
def _reset_skin_fonts_memo():
    """ensure_generated memoizes per addon_id; clear it so one test's cached
    path can never leak into the next test's assertions."""
    sf.reset_memo()
    yield

_SAMPLE = """<?xml version="1.0"?>
<fonts>
  <fontset id="Default" unicode="true">
    <font><name>font10</name><filename>a.ttf</filename><size>23</size></font>
    <font><name>Mini</name><filename>a.ttf</filename><size>24</size></font>
    <font><name>LargeNew</name><filename>b.ttf</filename><style>bold</style><size>44</size></font>
    <font><name>Null</name><filename>a.ttf</filename><size>0</size></font>
    <font><name>NoSize</name><filename>a.ttf</filename></font>
  </fontset>
  <fontset id="Other"><font><name>x</name><size>99</size></font></fontset>
</fonts>"""


def test_anchor_sizes():
    assert ANCHOR_SIZES == {"font36_title": 36, "font13": 30, "font12": 25, "font10": 23}


def test_parse_default_fontset():
    fonts = parse_fontset(_SAMPLE, "Default")
    assert fonts == {"font10": 23, "Mini": 24, "LargeNew": 44}


def test_parse_skips_zero_and_missing_size():
    fonts = parse_fontset(_SAMPLE, "Default")
    assert "Null" not in fonts and "NoSize" not in fonts


def test_parse_named_fontset():
    assert parse_fontset(_SAMPLE, "Other") == {"x": 99}


def test_parse_unknown_fontset_falls_back_to_first():
    assert parse_fontset(_SAMPLE, "Missing") == {"font10": 23, "Mini": 24, "LargeNew": 44}


def test_parse_garbage_returns_empty():
    assert parse_fontset("not xml", "Default") == {}


def test_parse_rejects_doctype_entity():
    # A malicious skin could craft a Font.xml with entity-expansion (billion
    # laughs). Legitimate font files never declare a DOCTYPE/ENTITY; reject them.
    hostile = ('<?xml version="1.0"?><!DOCTYPE fonts [<!ENTITY a "aaaa">]>'
               '<fonts><fontset id="Default"><font><name>font10</name>'
               '<size>23</size></font></fontset></fonts>')
    assert parse_fontset(hostile, "Default") == {}


def test_parse_drops_font_names_with_metacharacters():
    # A crafted font name that would inject markup if substituted unescaped.
    # It parses as valid XML (entity-encoded), so ET.fromstring succeeds; the
    # allowlist must drop it so it can never reach the generated dialog XML.
    injected = ('<fonts><fontset id="Default">'
                '<font><name>x&lt;/font&gt;&lt;onclick&gt;RunScript(evil)'
                '&lt;/onclick&gt;&lt;font&gt;</name><size>36</size></font>'
                '<font><name>font10</name><size>23</size></font>'
                '</fontset></fonts>')
    assert parse_fontset(injected, "Default") == {"font10": 23}


def test_parse_rejects_oversized_input():
    bomb = "<fonts><fontset id='Default'>" + ("<font><name>a</name><size>1</size></font>" * 100000)
    assert len(bomb) > 512 * 1024
    assert parse_fontset(bomb, "Default") == {}


def test_shipped_templates_only_use_anchor_fonts():
    # Guards ANCHOR_SIZES <-> template drift: substitute_fonts only remaps exact
    # anchor names, so a template introducing a new/misspelled <font> would
    # silently never adapt. Run from the repo root.
    import glob
    import re as _re
    used = set()
    files = glob.glob("resources/skins/Default/1080i/*.xml")
    assert files, "no shipped dialog XML found"
    for path in files:
        with open(path, "r", encoding="utf-8") as fh:
            used |= set(_re.findall(r"<font>([^<]+)</font>", fh.read()))
    assert used <= set(ANCHOR_SIZES), (
        "templates use non-anchor fonts: %s" % (used - set(ANCHOR_SIZES)))


def test_every_font_tag_uses_bare_form():
    # substitute_fonts only rewrites the exact <font>NAME</font> byte form (no
    # attributes, no surrounding whitespace/newline). A shipped dialog XML that
    # drifts from that bare form would silently never get font-adapted.
    import glob
    import re as _re
    files = glob.glob("resources/skins/Default/1080i/*.xml")
    assert files, "no shipped dialog XML found"
    for path in files:
        with open(path, "r", encoding="utf-8") as fh:
            text = fh.read()
        assert _re.search(r"<font\s", text) is None, "%s has attributed <font>" % path
        assert _re.search(r"<font>\s|\s</font>", text) is None, "%s has padded <font>" % path


def test_generate_into_copies_all_shipped_subdirs():
    # _generate_into only copies the 1080i XML dir and the media dir (see
    # skin_fonts._XML_DIR / _MEDIA_DIR). If Default/ ever ships a third subdir,
    # _generate_into would silently drop it from the adapted tree.
    skin_dir = os.path.join("resources", "skins", "Default")
    subdirs = {d for d in os.listdir(skin_dir)
               if os.path.isdir(os.path.join(skin_dir, d))}
    assert subdirs == {"1080i", "media"}, (
        "Default/ ships %s; _generate_into only copies {1080i, media}. Add the "
        "new subdir to _generate_into or this feature silently drops it." % subdirs)


def test_build_font_map_identity_when_anchor_present():
    # A skin that defines our anchor names maps each to itself.
    skin = {"font36_title": 36, "font13": 30, "font12": 25, "font10": 23}
    assert build_font_map(skin) == {
        "font36_title": "font36_title", "font13": "font13",
        "font12": "font12", "font10": "font10"}


def test_build_font_map_nearest_size():
    # Arctic-like: only font13 numbered, plus its own named fonts.
    skin = {"font13": 30, "Mini": 24, "Small20": 17, "LargeNew": 44, "Large": 38}
    m = build_font_map(skin)
    assert m["font36_title"] == "Large"    # 36 -> 38 (nearest, beats 44)
    assert m["font13"] == "font13"          # 30 -> 30 exact
    assert m["font12"] == "Mini"            # 25 -> 24 (nearest, beats 30)
    assert m["font10"] == "Mini"            # 23 -> 24 (nearest, beats 17)


def test_build_font_map_skips_special_fonts():
    # A symbol/icon font that is nearest by SIZE must not be chosen for text.
    skin = {"font13": 30, "SymbolList": 22, "Mini": 24}
    m = build_font_map(skin)
    assert m["font10"] == "Mini"  # 23 -> Mini(24), not SymbolList(22) despite closer size
    assert "SymbolList" not in m.values()


def test_build_font_map_empty_skin_is_identity():
    assert build_font_map({}) == {
        "font36_title": "font36_title", "font13": "font13",
        "font12": "font12", "font10": "font10"}


def test_substitute_fonts_replaces_anchor_tags():
    xml = "<font>font36_title</font> x <font>font10</font> <font>font10</font>"
    out = substitute_fonts(xml, {"font36_title": "Large", "font10": "Mini"})
    assert out == "<font>Large</font> x <font>Mini</font> <font>Mini</font>"


def test_substitute_fonts_identity_leaves_text_unchanged():
    xml = "<font>font10</font>"
    assert substitute_fonts(xml, {"font10": "font10"}) == xml


def test_cache_key_stable_and_sensitive():
    a = cache_key("skin.x", "1.0", "Default", "2.0", 1000)
    assert a == cache_key("skin.x", "1.0", "Default", "2.0", 1000)
    assert a != cache_key("skin.x", "1.1", "Default", "2.0", 1000)
    assert a != cache_key("skin.y", "1.0", "Default", "2.0", 1000)
    assert a != cache_key("skin.x", "1.0", "Default", "2.0", 1001)  # Font.xml edited


def test_generate_into_writes_substituted_xml(tmp_path):
    # Arrange a fake shipped addon tree.
    ship = tmp_path / "addon"
    res = ship / "resources" / "skins" / "Default"
    (res / "1080i").mkdir(parents=True)
    (res / "media" / "common").mkdir(parents=True)
    (res / "1080i" / "script-easytv-info.xml").write_text(
        "<window><control><font>font36_title</font></control></window>")
    (res / "media" / "common" / "white.png").write_text("PNG")

    out = tmp_path / "gen"
    font_map = {"font36_title": "LargeNew"}
    sf._generate_into(str(ship), str(out), font_map)

    gen_xml = out / "resources" / "skins" / "Default" / "1080i" / "script-easytv-info.xml"
    assert "<font>LargeNew</font>" in gen_xml.read_text()
    # media copied
    assert (out / "resources" / "skins" / "Default" / "media" / "common" / "white.png").exists()


def test_ensure_generated_falls_back_on_error(monkeypatch):
    # A failure mid-generation returns the shipped path, never raises.
    monkeypatch.setattr(sf, "_safe_shipped", lambda addon_id: "/ship/path")
    monkeypatch.setattr(sf, "_active_skin", lambda: (_ for _ in ()).throw(OSError("no skin")))
    assert sf.ensure_generated("script.easytv") == "/ship/path"


def test_ensure_generated_fallback_never_raises(monkeypatch):
    # Even if xbmcaddon.Addon() itself raises (malformed/unregistered id), the
    # caller gets a string, never an exception (the "never break a dialog"
    # invariant, which the fallback path must not itself violate).
    monkeypatch.setattr(sf.xbmcaddon, "Addon",
                        lambda addon_id: (_ for _ in ()).throw(RuntimeError("no addon")))
    monkeypatch.setattr(sf.xbmcvfs, "translatePath", lambda p: "/home/addons/x")
    assert sf.ensure_generated("script.easytv") == "/home/addons/x"


def test_ensure_generated_rejects_bad_addon_id(monkeypatch):
    monkeypatch.setattr(sf, "_safe_shipped", lambda a: "/ship")
    assert sf.ensure_generated("../evil") == "/ship"


def test_memo_skips_probe_within_ttl(monkeypatch):
    sf.reset_memo()
    calls = {"fontset": 0}
    monkeypatch.setattr(sf.xbmc, "getSkinDir", lambda: "skin.estuary")
    monkeypatch.setattr(sf, "_active_fontset", lambda: (calls.__setitem__("fontset", calls["fontset"] + 1) or "Default"))
    # Make the full path return a known value the first time. It stands in for
    # the real _compute_generated_path, which is what actually calls
    # _active_fontset (the RPC probe) on a genuine cache miss.
    monkeypatch.setattr(sf, "_compute_generated_path",
                        lambda addon_id, skin_id: sf._active_fontset() and "/gen")
    t = {"v": 1000.0}
    monkeypatch.setattr(sf.time, "monotonic", lambda: t["v"])
    assert sf.ensure_generated("script.easytv") == "/gen"
    assert sf.ensure_generated("script.easytv") == "/gen"   # within TTL
    assert calls["fontset"] == 1                            # probe ran once
    t["v"] += sf._MEMO_TTL + 1                              # expire
    assert sf.ensure_generated("script.easytv") == "/gen"
    assert calls["fontset"] == 2                            # re-probed after TTL


def test_memo_invalidates_on_skin_change(monkeypatch):
    sf.reset_memo()
    skin = {"v": "skin.estuary"}
    monkeypatch.setattr(sf.xbmc, "getSkinDir", lambda: skin["v"])
    monkeypatch.setattr(sf, "_active_fontset", lambda: "Default")
    seen = []
    monkeypatch.setattr(sf, "_compute_generated_path",
                        lambda addon_id, skin_id: seen.append(skin_id) or ("/gen/" + skin_id))
    monkeypatch.setattr(sf.time, "monotonic", lambda: 1000.0)
    assert sf.ensure_generated("script.easytv") == "/gen/skin.estuary"
    skin["v"] = "skin.arctic"
    assert sf.ensure_generated("script.easytv") == "/gen/skin.arctic"
    assert seen == ["skin.estuary", "skin.arctic"]


def test_resolve_params_literal_passthrough():
    assert sf._resolve_params("28", {}) == "28"


def test_resolve_params_substitutes_from_scope():
    assert sf._resolve_params("$PARAM[size_main]", {"size_main": "28"}) == "28"


def test_resolve_params_missing_key_is_none():
    assert sf._resolve_params("$PARAM[nope]", {"size_main": "28"}) is None


def test_resolve_params_dynamic_token_is_none():
    # $VAR/$INFO/skinvariable etc. cannot be resolved -> None (font gets skipped)
    assert sf._resolve_params("$VAR[FontSize]", {}) is None
    assert sf._resolve_params("$INFO[Skin.String(x)]", {}) is None


def test_resolve_params_none_input_is_none():
    assert sf._resolve_params(None, {}) is None


def test_build_include_table_collects_named_includes():
    a = "<includes><include name='Foo'><font><name>x</name><size>10</size></font></include></includes>"
    b = "<includes><include name='Bar'/></includes>"
    tbl = sf.build_include_table([a, b])
    assert set(tbl) == {"Foo", "Bar"}


def test_build_include_table_ignores_invocations_and_guards():
    # <include content=..> and bare <include>text</include> are invocations, not defs
    inv = "<includes><include content='Foo'/><include>Bar</include></includes>"
    assert sf.build_include_table([inv]) == {}
    # per-file guards: DOCTYPE and oversize files are skipped, not fatal
    hostile = "<!DOCTYPE x [<!ENTITY e 'y'>]><includes><include name='Z'/></includes>"
    big = "<includes>" + "<include name='Q'/>" * 100000 + "</includes>"
    assert "Z" not in sf.build_include_table([hostile])
    assert len(big) > 512 * 1024 and "Q" not in sf.build_include_table([big])


def test_build_include_table_first_definition_wins():
    a = "<includes><include name='Foo'><font><name>a</name><size>1</size></font></include></includes>"
    b = "<includes><include name='Foo'><font><name>b</name><size>2</size></font></include></includes>"
    tbl = sf.build_include_table([a, b])
    assert tbl["Foo"].find("font/name").text == "a"


# A Fuse-shaped skin: fontset references Font_Default via <include>; the real
# fonts live in a sibling include file with $PARAM sizes + a nested include.
_FUSE_FONTSET = "<fonts><fontset id='Default'><include>Font_Default</include></fontset></fonts>"
_FUSE_INCLUDES = """<includes>
  <include name="Font_Static">
    <definition>
      <font><name>font_main_iconic</name><filename>fa.ttf</filename><size>30</size></font>
    </definition>
  </include>
  <include name="Font_Default">
    <param name="size_tiny">21</param>
    <param name="size_main">28</param>
    <param name="size_head">38</param>
    <definition>
      <include content="Font_Static"/>
      <font><name>font10</name><size>$PARAM[size_tiny]</size></font>
      <font><name>font13</name><size>$PARAM[size_main]</size></font>
      <font><name>font_head</name><size>$PARAM[size_head]</size></font>
      <font><name>font_bad</name><size>$VAR[Dynamic]</size></font>
    </definition>
  </include>
</includes>"""


def test_parse_fontset_resolves_parameterized_include():
    tbl = sf.build_include_table([_FUSE_INCLUDES])
    fonts = sf.parse_fontset(_FUSE_FONTSET, "Default", tbl)
    assert fonts["font10"] == 21
    assert fonts["font13"] == 28
    assert fonts["font_head"] == 38
    # nested include resolves its own literal-size font
    assert fonts["font_main_iconic"] == 30


def test_parse_fontset_skips_unresolvable_font_but_keeps_rest():
    tbl = sf.build_include_table([_FUSE_INCLUDES])
    fonts = sf.parse_fontset(_FUSE_FONTSET, "Default", tbl)
    assert "font_bad" not in fonts          # $VAR -> omitted, not fatal
    assert fonts                            # the resolvable fonts still came through


def test_parse_fontset_without_includes_is_inline_only():
    # Existing behavior: no include table -> fontset <include> yields nothing extra
    assert sf.parse_fontset(_FUSE_FONTSET, "Default") == {}
    assert sf.parse_fontset(_FUSE_FONTSET, "Default", {}) == {}


def test_parse_fontset_unknown_include_name_is_empty():
    assert sf.parse_fontset(_FUSE_FONTSET, "Default", {}) == {}


def test_expand_include_depth_guard_stops_cycle():
    cyc = "<includes><include name='A'><definition><include content='A'/></definition></include></includes>"
    tbl = sf.build_include_table([cyc])
    assert sf._expand_include("A", tbl, {}, 0) == {}   # no infinite recursion


def test_expand_include_ignores_conditional_includes():
    xml = ("<includes><include name='A'><definition>"
           "<include content='B' condition='Skin.HasSetting(x)'/>"
           "<font><name>font13</name><size>28</size></font>"
           "</definition></include>"
           "<include name='B'><definition>"
           "<font><name>font10</name><size>21</size></font></definition></include></includes>")
    tbl = sf.build_include_table([xml])
    out = sf._expand_include("A", tbl, {}, 0)
    assert out == {"font13": 28}            # conditional branch skipped


def test_expand_include_allowlists_resolved_names():
    xml = ("<includes><include name='A'><definition>"
           "<font><name>bad&lt;name</name><size>20</size></font>"
           "<font><name>font13</name><size>28</size></font>"
           "</definition></include></includes>")
    tbl = sf.build_include_table([xml])
    assert sf._expand_include("A", tbl, {}, 0) == {"font13": 28}


def test_expand_include_allowlists_param_assembled_name():
    # The allowlist must apply to the RESOLVED name, AFTER $PARAM substitution:
    # a param whose value decodes to an XML metacharacter, used as a font name,
    # must be dropped so it can never reach the generated <font>NAME</font>.
    xml = ("<includes><include name='A'>"
           "<param name='evil'>x&lt;/font&gt;</param>"
           "<definition>"
           "<font><name>$PARAM[evil]</name><size>30</size></font>"
           "<font><name>font13</name><size>28</size></font>"
           "</definition></include></includes>")
    tbl = sf.build_include_table([xml])
    assert sf._expand_include("A", tbl, {}, 0) == {"font13": 28}


def test_parse_fontset_inline_and_include_merge_inline_wins():
    xml = ("<fonts><fontset id='Default'>"
           "<font><name>font13</name><size>99</size></font>"
           "<include>Foo</include></fontset></fonts>")
    inc = "<includes><include name='Foo'><definition><font><name>font13</name><size>28</size></font><font><name>font10</name><size>21</size></font></definition></include></includes>"
    tbl = sf.build_include_table([inc])
    fonts = sf.parse_fontset(xml, "Default", tbl)
    assert fonts["font13"] == 99            # inline definition wins
    assert fonts["font10"] == 21


def test_font_relevant_xml_filters():
    names = ["Font.xml", "Includes_Font.xml", "Includes.xml", "Home.xml",
             "DialogSelect.xml", "font_extra.xml", "notxml.txt"]
    got = set(sf._font_relevant_xml(names))
    assert "Font.xml" in got
    assert "Includes_Font.xml" in got
    assert "Includes.xml" in got            # starts with "includes"
    assert "font_extra.xml" in got
    assert "Home.xml" not in got            # unrelated dialog XML excluded
    assert "notxml.txt" not in got


def test_load_skin_includes_reads_sibling_xml(tmp_path):
    d = tmp_path / "1080i"
    d.mkdir()
    (d / "Font.xml").write_text("<fonts><fontset id='Default'><include>Font_Default</include></fontset></fonts>")
    (d / "Includes_Font.xml").write_text(
        "<includes><include name='Font_Default'><definition>"
        "<font><name>font13</name><size>28</size></font></definition></include></includes>")
    (d / "notxml.txt").write_text("ignore me")
    names = os.listdir(str(d))
    tbl = sf._load_skin_includes(str(d), names)
    assert "Font_Default" in tbl


def test_load_skin_includes_empty_names_returns_empty():
    # Caller passes [] when the directory listing itself failed (see the
    # os.listdir try/except in _compute_generated_path); the loader must
    # degrade to {} rather than raise.
    assert sf._load_skin_includes("/whatever", []) == {}


def test_load_skin_includes_skips_unreadable_file(tmp_path):
    # One sibling file that cannot be opened must not block the rest: a
    # directory named "BadFont.xml" makes open() raise IsADirectoryError (an
    # OSError subclass), while "GoodFont.xml" still resolves normally. Both
    # names must be font-relevant (contain "font") or _font_relevant_xml
    # would exclude them before either is ever opened.
    d = tmp_path / "1080i"
    d.mkdir()
    (d / "BadFont.xml").mkdir()
    (d / "GoodFont.xml").write_text(
        "<includes><include name='Font_Default'><definition>"
        "<font><name>font13</name><size>28</size></font></definition></include></includes>")
    names = os.listdir(str(d))
    tbl = sf._load_skin_includes(str(d), names)
    assert "Font_Default" in tbl


def test_ensure_generated_adapts_parameterized_skin(tmp_path, monkeypatch):
    # Fake skin dir: Font.xml (include-based) + sibling include file with $PARAM.
    skin = tmp_path / "skin" / "1080i"
    skin.mkdir(parents=True)
    (skin / "Font.xml").write_text(
        "<fonts><fontset id='Default'><include>Font_Default</include></fontset></fonts>")
    (skin / "Includes_Font.xml").write_text(
        "<includes><include name='Font_Default'>"
        "<param name='size_main'>28</param><param name='size_head'>38</param>"
        "<definition>"
        "<font><name>font13</name><size>$PARAM[size_main]</size></font>"
        "<font><name>font_head</name><size>$PARAM[size_head]</size></font>"
        "</definition></include></includes>")

    # Fake shipped addon tree with one dialog that uses the title anchor.
    ship = tmp_path / "addon"
    res = ship / "resources" / "skins" / "Default" / "1080i"
    res.mkdir(parents=True)
    (res / "script-easytv-info.xml").write_text(
        "<window><control><font>font36_title</font></control></window>")
    (ship / "resources" / "skins" / "Default" / "media").mkdir(parents=True)

    out = tmp_path / "data"

    class _A:
        def getAddonInfo(self, k):
            return {"path": str(ship), "version": "1.0.0"}[k]
    monkeypatch.setattr(sf.xbmcaddon, "Addon", lambda addon_id: _A())
    monkeypatch.setattr(sf, "_active_skin", lambda: ("skin.fuse", "3.0"))
    monkeypatch.setattr(sf, "_active_fontset", lambda: "Default")
    monkeypatch.setattr(sf, "_find_skin_font_xml", lambda: str(skin / "Font.xml"))
    monkeypatch.setattr(sf.xbmcvfs, "translatePath",
                        lambda p: str(out / "skingen") if "skingen" in p else str(out))

    path = sf.ensure_generated("script.easytv")
    gen = out / "skingen" / "resources" / "skins" / "Default" / "1080i" / "script-easytv-info.xml"
    # font36_title(36) -> nearest resolved text font is font_head(38), not the shipped anchor
    assert "<font>font_head</font>" in gen.read_text()
    assert path == str(out / "skingen")


def test_ensure_generated_survives_listdir_error(tmp_path, monkeypatch):
    # If os.listdir on the skin's Font.xml directory raises (removed mid-scan,
    # permissions, network share hiccup), the multi-file mtime scan must
    # degrade to Font.xml's own mtime and the caller must still get a valid
    # scriptPath back, never an exception.
    skin = tmp_path / "skin" / "1080i"
    skin.mkdir(parents=True)
    (skin / "Font.xml").write_text(
        "<fonts><fontset id='Default'><include>Font_Default</include></fontset></fonts>")

    ship = tmp_path / "addon"
    res = ship / "resources" / "skins" / "Default" / "1080i"
    res.mkdir(parents=True)
    (res / "script-easytv-info.xml").write_text(
        "<window><control><font>font36_title</font></control></window>")
    (ship / "resources" / "skins" / "Default" / "media").mkdir(parents=True)

    out = tmp_path / "data"

    class _A:
        def getAddonInfo(self, k):
            return {"path": str(ship), "version": "1.0.0"}[k]
    monkeypatch.setattr(sf.xbmcaddon, "Addon", lambda addon_id: _A())
    monkeypatch.setattr(sf, "_active_skin", lambda: ("skin.fuse", "3.0"))
    monkeypatch.setattr(sf, "_active_fontset", lambda: "Default")
    monkeypatch.setattr(sf, "_find_skin_font_xml", lambda: str(skin / "Font.xml"))
    monkeypatch.setattr(sf.xbmcvfs, "translatePath",
                        lambda p: str(out / "skingen") if "skingen" in p else str(out))

    real_listdir = sf.os.listdir

    def fake_listdir(path):
        if path == str(skin):
            raise OSError("directory vanished")
        return real_listdir(path)
    monkeypatch.setattr(sf.os, "listdir", fake_listdir)

    path = sf.ensure_generated("script.easytv")
    assert isinstance(path, str) and path


def test_parse_fontset_rejects_multibyte_over_byte_cap():
    # len(str) under cap, UTF-8 bytes over cap -> rejected. The ballast lives in
    # <filename> (unread by parse_fontset) so the extracted font name stays
    # short and valid; only the byte-length cap check can make this {}. "é" is
    # 1 codepoint but 2 UTF-8 bytes, so a large-enough repeat count crosses the
    # byte cap while the codepoint count stays under it.
    font = ("<font><name>font10</name><filename>" + ("é" * 280000)
           + "</filename><size>23</size></font>")
    payload = "<fonts><fontset id='Default'>%s</fontset></fonts>" % font
    assert len(payload) < sf._MAX_FONT_XML_BYTES
    assert len(payload.encode("utf-8")) > sf._MAX_FONT_XML_BYTES
    assert sf.parse_fontset(payload, "Default") == {}


def test_read_font_xml_skips_oversized(tmp_path):
    big = tmp_path / "Font.xml"
    big.write_bytes(b"x" * (sf._MAX_FONT_XML_BYTES + 1))
    assert sf._read_font_xml(str(big)) is None


def test_read_font_xml_reads_small(tmp_path):
    small = tmp_path / "Font.xml"
    small.write_text("<fonts/>", encoding="utf-8")
    assert sf._read_font_xml(str(small)) == "<fonts/>"


def test_valid_font_name_rejects_trailing_newline():
    assert sf._VALID_FONT_NAME.match("font10") is not None
    assert sf._VALID_FONT_NAME.match("font10\n") is None


def test_ensure_generated_rejects_dotdot_addon_id(monkeypatch):
    called = {}
    def mock_safe_shipped(aid):
        called["id"] = aid
        return "/shipped"
    monkeypatch.setattr(sf, "_safe_shipped", mock_safe_shipped)
    assert sf.ensure_generated("..") == "/shipped"
    assert sf.ensure_generated(".") == "/shipped"
    assert called["id"] in (".", "..")


def test_cleanup_orphans_removes_stale_new_and_old(tmp_path):
    import os
    import time

    import resources.lib.ui.skin_fonts as sf
    out_base = str(tmp_path / "skingen")
    os.makedirs(out_base + ".new.99999")   # orphan from a dead pid
    old = time.time() - (sf._LOCK_STALE_SECS + 5)
    os.utime(out_base + ".new.99999", (old, old))  # age it past the stale threshold
    os.makedirs(out_base + ".old")
    keep = out_base + ".new." + str(os.getpid())
    os.makedirs(keep)
    sf._cleanup_orphans(out_base, keep)
    assert not os.path.isdir(out_base + ".new.99999")
    assert not os.path.isdir(out_base + ".old")
    assert os.path.isdir(keep)             # our own tmp is preserved


def test_cleanup_orphans_preserves_fresh_foreign_new(tmp_path):
    """A fresh .new.<otherpid> may belong to a live concurrent builder; only a
    stale one (older than _LOCK_STALE_SECS) is safe to sweep."""
    import os

    import resources.lib.ui.skin_fonts as sf
    out_base = str(tmp_path / "skingen")
    fresh_foreign = out_base + ".new.12345"
    os.makedirs(fresh_foreign)             # freshly created: mtime is "now"
    stale_foreign = out_base + ".new.99999"
    os.makedirs(stale_foreign)
    old = time.time() - (sf._LOCK_STALE_SECS + 5)
    os.utime(stale_foreign, (old, old))
    os.makedirs(out_base + ".old")
    keep = out_base + ".new." + str(os.getpid())
    os.makedirs(keep)
    sf._cleanup_orphans(out_base, keep)
    assert os.path.isdir(fresh_foreign)    # live concurrent builder: preserved
    assert not os.path.isdir(stale_foreign)  # crashed builder: removed
    assert not os.path.isdir(out_base + ".old")
    assert os.path.isdir(keep)             # our own tmp is preserved


def test_fsync_path_best_effort_never_raises(tmp_path):
    # _fsync_path must swallow errors on a path that cannot be fsynced.
    sf._fsync_path(str(tmp_path / "does-not-exist"))   # must not raise


def test_try_lock_atomic_reclaim(tmp_path):
    lock = str(tmp_path / "x.lock")
    open(lock, "w").close()
    old = time.time() - (sf._LOCK_STALE_SECS + 5)
    os.utime(lock, (old, old))              # make it stale
    fd = sf._try_lock(lock)
    assert fd is not None                    # stale lock reclaimed
    sf._release_lock(fd, lock)


def test_try_lock_non_stale_not_reclaimed(tmp_path):
    lock = str(tmp_path / "x.lock")
    open(lock, "w").close()                 # fresh mtime: not stale
    assert sf._try_lock(lock) is None


def test_try_lock_failed_rename_backs_off(tmp_path, monkeypatch):
    lock = str(tmp_path / "x.lock")
    open(lock, "w").close()
    old = time.time() - (sf._LOCK_STALE_SECS + 5)
    os.utime(lock, (old, old))              # make it stale

    def _boom(_src, _dst):
        raise OSError("simulated: another racer already reclaimed it")

    monkeypatch.setattr(sf.os, "rename", _boom)
    assert sf._try_lock(lock) is None       # loses the race: does not steal
