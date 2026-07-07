"""
Skin-adaptive fonts for EasyTV custom dialogs.

Kodi resolves a control's <font> against the active skin's font set only, with a
hard fallback to font13; addons cannot ship or register their own fonts for a
WindowXMLDialog. This module adapts our dialogs to the active skin: it parses the
skin's Font.xml, maps our anchor font names to the nearest-size font the skin
actually defines, writes font-substituted copies of the dialog XML into
addon_data, and returns a scriptPath the dialogs load from. Any failure falls
back to the shipped addon path (dialogs then render as before).

DELETION GUIDE (KODI-FONT-WORKAROUND, kodi#28534):
    This entire module exists only to work around a Kodi limitation: addons
    cannot register fonts for their WindowXML/WindowXMLDialog windows. It is
    tracked upstream at https://github.com/xbmc/xbmc/issues/28534. When that
    lands (an addon can ship/register its own fonts), delete all of this:
      1. Delete this module (skin_fonts.py) and tests/test_skin_fonts.py.
      2. At every call site, drop the ensure_generated(...) indirection and
         pass the shipped addon path to the dialog scriptPath instead. Find
         them all with:  grep -rn "KODI-FONT-WORKAROUND" resources/
      3. The shipped dialog XML can then reference real registered fonts
         directly, so the font-name anchors need no substitution.

Logging:
    Logger: 'ui'
    Key events:
        - skinfont.generate (INFO): Generated adapted XML for a skin
        - skinfont.fallback (WARNING): Generation failed; using shipped path
    See LOGGING.md for full guidelines.
"""
from __future__ import annotations

import os
import re
import shutil
import time
import xml.etree.ElementTree as ET
from typing import Dict, Iterable, List, Optional, Tuple

import xbmc
import xbmcaddon
import xbmcvfs

from resources.lib.utils import get_logger

log = get_logger('ui')

# Generated dialog XML embeds mapped font NAMES (from the skin Font.xml) as
# <font>NAME</font> via plain text substitution, so a name MUST be free of any
# XML metacharacter. Allowlist at parse time: a hostile or metacharacter-bearing
# name is dropped (never mapped), which both blocks markup/action injection and
# guarantees the generated XML stays well-formed (so the fallback invariant holds).
_VALID_FONT_NAME = re.compile(r"^[A-Za-z0-9_.]{1,64}$")  # bounded length: a
# multi-KB font name would be spliced into every <font> occurrence (font10 is
# used 48x), amplifying the generated tree to tens of MB from a sub-cap input.
# Real skin fontsets are a few KB; cap input to avoid a flat-XML resource bomb.
_MAX_FONT_XML_BYTES = 512 * 1024

# Parameterized-include support (Fuse-style skins define fonts inside
# <include name="..."><param name="size_main">28</param>... and reference
# $PARAM[size_main] as a font size). Bounded by design: $VAR/$INFO/$EXP and
# skinvariable tokens are dynamic (only resolvable at Kodi render time) and are
# never evaluated here; a font using one is omitted rather than guessed.
_PARAM_RE = re.compile(r"\$PARAM\[([A-Za-z0-9_]+)\]")
_MAX_INCLUDE_DEPTH = 8
_UNRESOLVED = "\x00"  # sentinel: a $PARAM key absent from scope

# Anchor font names used in the dialog XML, keyed to their Estuary sizes (the
# target sizes we designed against).
ANCHOR_SIZES: Dict[str, int] = {
    "font36_title": 36,
    "font13": 30,
    "font12": 25,
    "font10": 23,
}


def _resolve_params(text: Optional[str], scope: Dict[str, str]) -> Optional[str]:
    """Substitute $PARAM[key] from `scope`. Return None (unresolvable) if any
    key is absent, or if any '$' token survives substitution (a $VAR/$INFO/$EXP
    or skinvariable we deliberately do not evaluate). Literal text passes
    through unchanged."""
    if text is None:
        return None
    out = _PARAM_RE.sub(lambda m: scope.get(m.group(1), _UNRESOLVED), text)
    if _UNRESOLVED in out or "$" in out:
        return None
    return out


def build_include_table(xml_texts: Iterable[str]) -> Dict[str, "ET.Element"]:
    """Map every <include name="X"> element across the given skin XML file
    contents. Applies the same per-file guards as parse_fontset (size cap,
    DOCTYPE/ENTITY reject, parse-error skip). First definition of a name wins.
    Invocation elements (<include content=..> / <include>text</include>) are
    not definitions and are ignored here.

    Note the size cap is also a functional ceiling: a skin that defines its font
    include inside an oversized XML file is skipped here, so its fontset
    <include> resolves to nothing and the skin degrades to identity (no
    adaptation). That is a safe no-op, never a broken dialog."""
    table: Dict[str, "ET.Element"] = {}
    for text in xml_texts:
        if not text or len(text) > _MAX_FONT_XML_BYTES:
            continue
        low = text.lower()
        if "<!doctype" in low or "<!entity" in low:
            continue
        try:
            root = ET.fromstring(text)
        except ET.ParseError:
            continue
        for inc in root.iter("include"):
            name = inc.get("name")
            if name and name not in table:
                table[name] = inc
    return table


def _expand_include(name: str, includes: Dict[str, "ET.Element"],
                    overrides: Dict[str, str], depth: int) -> Dict[str, int]:
    """Expand include `name` into {font_name: size}, resolving $PARAM against the
    param scope (the include's <param> defaults, overridden by `overrides`).
    Bounded and bail-safe: an unknown name, depth past _MAX_INCLUDE_DEPTH, a
    conditional include, or an unresolvable/non-integer size omits that font (or
    branch) rather than raising or guessing."""
    if depth > _MAX_INCLUDE_DEPTH:
        return {}
    defn = includes.get(name)
    if defn is None:
        return {}
    scope: Dict[str, str] = {}
    for p in defn.findall("param"):
        pname = p.get("name")
        if not pname:
            continue
        if pname in overrides:
            scope[pname] = overrides[pname]
        else:
            resolved = _resolve_params(p.text or "", scope)
            scope[pname] = resolved if resolved is not None else (p.text or "")
    for k, v in overrides.items():
        scope.setdefault(k, v)

    definition = defn.find("definition")
    body = definition if definition is not None else defn
    result: Dict[str, int] = {}
    for child in body:
        if child.tag == "font":
            name_el = child.find("name")
            size_el = child.find("size")
            if name_el is None or size_el is None:
                continue
            fname = _resolve_params((name_el.text or "").strip(), scope)
            fsize = _resolve_params((size_el.text or "").strip(), scope)
            if fname is None or fsize is None:
                continue
            try:
                size = int(fsize)
            except ValueError:
                continue
            if fname and size > 0 and _VALID_FONT_NAME.match(fname):
                result[fname] = size
        elif child.tag == "include":
            if child.get("condition"):
                continue
            sub = child.get("content") or (child.text or "").strip()
            if not sub:
                continue
            sub_over: Dict[str, str] = {}
            for p in child.findall("param"):
                pn = p.get("name")
                if not pn:
                    continue
                rv = _resolve_params(p.text or "", scope)
                sub_over[pn] = rv if rv is not None else (p.text or "")
            for fn, sz in _expand_include(sub, includes, sub_over, depth + 1).items():
                result.setdefault(fn, sz)
    return result


def parse_fontset(font_xml_text: str, fontset_id: str = "Default",
                  includes: Optional[Dict[str, "ET.Element"]] = None) -> Dict[str, int]:
    """Parse a skin Font.xml into {font_name: size} for the given fontset.

    Falls back to the first fontset if `fontset_id` is absent. Fonts without a
    positive integer size are skipped. Returns {} on any parse error.

    Some skins (e.g. Fuse-based ones) define a fontset as one or more
    <include>NAME</include> references into a separate includes file, with the
    actual <font> definitions and $PARAM[...] sizes living in that include.
    Pass the table built by `build_include_table` as `includes` to resolve
    those; the default (None or {}) keeps this to inline <font> parsing only,
    matching the original behavior. Where a font name is defined both inline
    and via an include, the inline definition wins.

    Security (input is a third-party skin's Font.xml):
    - Reject input over `_MAX_FONT_XML_BYTES` (flat-XML resource bomb).
    - Reject any DOCTYPE/ENTITY declaration (billion-laughs); stdlib ElementTree
      already does not resolve external entities (XXE) on Python 3.7.1+.
    - Allowlist font names to `_VALID_FONT_NAME`; a name carrying any XML
      metacharacter is dropped, so the downstream text substitution can neither
      be injected nor produce malformed XML (no defusedxml dependency needed).
    """
    if len(font_xml_text) > _MAX_FONT_XML_BYTES:
        return {}
    lowered = font_xml_text.lower()
    if "<!doctype" in lowered or "<!entity" in lowered:
        return {}
    try:
        root = ET.fromstring(font_xml_text)
    except ET.ParseError:
        return {}
    fontsets = root.findall("fontset")
    chosen = None
    for fs in fontsets:
        if fs.get("id") == fontset_id:
            chosen = fs
            break
    if chosen is None and fontsets:
        chosen = fontsets[0]
    if chosen is None:
        return {}
    result: Dict[str, int] = {}
    for font in chosen.findall("font"):
        name_el = font.find("name")
        size_el = font.find("size")
        if name_el is None or size_el is None:
            continue
        name = (name_el.text or "").strip()
        try:
            size = int((size_el.text or "").strip())
        except ValueError:
            continue
        if name and size > 0 and _VALID_FONT_NAME.match(name):
            result[name] = size
    if includes:
        for inc in chosen.findall("include"):
            if inc.get("condition"):
                continue
            sub = inc.get("content") or (inc.text or "").strip()
            if not sub:
                continue
            overrides: Dict[str, str] = {}
            for p in inc.findall("param"):
                pn = p.get("name")
                if not pn:
                    continue
                overrides[pn] = p.text or ""
            for fname, size in _expand_include(sub, includes, overrides, 0).items():
                result.setdefault(fname, size)   # inline fonts take precedence
    return result


# Skin fonts whose NAME signals a special-purpose glyph/symbol/decorative font
# rather than general body text. Nearest-size matching MUST skip these, or
# captions and labels render as icons/wrong glyphs (observed live: Arctic's
# "SymbolList" was nearest to font10 by size and rendered "Runtime" with a clock
# glyph and cast names in a symbol face).
_SPECIAL_FONT_HINTS = (
    "symbol", "icon", "glyph", "flag", "weather", "clock", "lyric", "mono",
    "arrow", "timeline", "selector", "watched", "wingding", "awesome",
    "material", "dingbat", "emoji",
)


def _is_text_font(name: str) -> bool:
    """True unless the font name signals a special-purpose (non-text) face."""
    low = name.lower()
    return not any(hint in low for hint in _SPECIAL_FONT_HINTS)


def build_font_map(skin_fonts: Dict[str, int],
                   anchors: Dict[str, int] = ANCHOR_SIZES) -> Dict[str, str]:
    """Map each anchor font name to the skin's nearest-size TEXT font.

    If the skin defines the anchor name itself, it maps to itself. Special-
    purpose fonts (symbol/icon/flag/weather/etc., by name) are excluded from the
    candidate pool so text never gets mapped onto a glyph face. If the skin
    provides no usable text font, an anchor maps to itself (identity), so the
    shipped name is kept and Kodi's own font13 fallback applies.
    """
    font_map: Dict[str, str] = {}
    candidates = {n: s for n, s in skin_fonts.items() if _is_text_font(n)}
    for anchor, target in anchors.items():
        if anchor in skin_fonts:
            font_map[anchor] = anchor
            continue
        if not candidates:
            font_map[anchor] = anchor
            continue
        # Nearest by absolute size difference; ties break to the smaller size
        # then the name, for determinism.
        best = min(candidates.items(),
                   key=lambda kv: (abs(kv[1] - target), kv[1], kv[0]))
        font_map[anchor] = best[0]
    return font_map


def substitute_fonts(xml_text: str, font_map: Dict[str, str]) -> str:
    """Replace <font>ANCHOR</font> with <font>MAPPED</font> for each anchor."""
    out = xml_text
    for anchor, mapped in font_map.items():
        if anchor != mapped:
            out = out.replace("<font>%s</font>" % anchor,
                              "<font>%s</font>" % mapped)
    return out


def cache_key(skin_id: str, skin_version: str, fontset: str,
              addon_version: str, font_mtime: int) -> str:
    """Stable identity for a generated set (invalidates on any component change).

    Includes the skin Font.xml mtime so a hand-edited or forked skin font file
    invalidates the cache without a per-open full content hash (TRADEOFF-1).
    """
    return "%s@%s|%s|addon@%s|font@%d" % (
        skin_id, skin_version, fontset, addon_version, font_mtime)


_RES_REL = os.path.join("resources", "skins", "Default")
_XML_DIR = os.path.join(_RES_REL, "1080i")
_MEDIA_DIR = os.path.join(_RES_REL, "media")
_MARKER = ".built-for"
_VALID_ID = re.compile(r"^[A-Za-z0-9_.]+$")
_LOCK_STALE_SECS = 30


def _safe_shipped(addon_id: str) -> str:
    """The shipped scriptPath, but NEVER raising: the fallback must not itself
    break a dialog. If Addon() fails (malformed/unregistered id), derive the
    conventional install path defensively."""
    try:
        return xbmcaddon.Addon(addon_id).getAddonInfo('path')
    except Exception:  # noqa: BLE001
        return xbmcvfs.translatePath("special://home/addons/%s" % addon_id)


def _active_skin() -> Tuple[str, str]:
    """Return (skin_id, skin_version). Raises if the skin addon is unavailable."""
    skin_id = xbmc.getSkinDir()
    version = xbmcaddon.Addon(skin_id).getAddonInfo('version')
    return skin_id, version


def _active_fontset() -> str:
    from resources.lib.utils import json_query
    try:
        res = json_query({"jsonrpc": "2.0", "method": "Settings.GetSettingValue",
                          "params": {"setting": "lookandfeel.font"}, "id": 1})
        value = res.get("value", "") if isinstance(res, dict) else ""
        return value or "Default"
    except Exception:  # noqa: BLE001
        return "Default"


def _find_skin_font_xml() -> Optional[str]:
    """Locate the active skin's Font.xml (varies by skin: 1080i/, xml/, etc.)."""
    base = xbmcvfs.translatePath("special://skin/")
    candidates = ["1080i", "16x9", "720p", "xml", "1080p", ""]
    for sub in candidates:
        path = os.path.join(base, sub, "Font.xml") if sub else os.path.join(base, "Font.xml")
        if os.path.isfile(path):
            return path
    # Last resort: shallow search one level down.
    try:
        for entry in os.listdir(base):
            path = os.path.join(base, entry, "Font.xml")
            if os.path.isfile(path):
                return path
    except OSError:
        pass
    return None


def _load_skin_includes(skin_xml_dir: str) -> Dict[str, "ET.Element"]:
    """Build the include table from every *.xml in the skin's resolution dir
    (where Arctic-family skins keep Includes_Font.xml). Best-effort: unreadable
    files are skipped. Returns {} if the directory cannot be listed."""
    texts: List[str] = []
    try:
        names = sorted(os.listdir(skin_xml_dir))
    except OSError:
        return {}
    for entry in names:
        if not entry.lower().endswith(".xml"):
            continue
        try:
            with open(os.path.join(skin_xml_dir, entry), "r", encoding="utf-8") as fh:
                texts.append(fh.read())
        except OSError:
            continue
    return build_include_table(texts)


def _try_lock(lock_path: str) -> Optional[int]:
    """Acquire an exclusive lockfile fd, or None if another process holds it.

    A lock older than _LOCK_STALE_SECS is reclaimed once (crashed writer)."""
    try:
        return os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        try:
            if time.time() - os.path.getmtime(lock_path) > _LOCK_STALE_SECS:
                os.remove(lock_path)
                return os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except (OSError, FileExistsError):
            return None
        return None


def _release_lock(fd: int, lock_path: str) -> None:
    try:
        os.close(fd)
    except OSError:
        pass
    try:
        os.remove(lock_path)
    except OSError:
        pass


def _generate_into(shipped_path: str, out_base: str, font_map: Dict[str, str]) -> None:
    """Build a COMPLETE adapted tree (every dialog XML + a full media copy) into
    out_base, which must not already exist. Media is copied every time (no
    existence gate) so an addon update ships new assets."""
    dst_xml = os.path.join(out_base, _XML_DIR)
    os.makedirs(dst_xml)
    src_xml = os.path.join(shipped_path, _XML_DIR)
    for name in os.listdir(src_xml):
        if not name.endswith(".xml"):
            continue
        with open(os.path.join(src_xml, name), "r", encoding="utf-8") as fh:
            text = fh.read()
        with open(os.path.join(dst_xml, name), "w", encoding="utf-8") as fh:
            fh.write(substitute_fonts(text, font_map))
    shutil.copytree(os.path.join(shipped_path, _MEDIA_DIR),
                    os.path.join(out_base, _MEDIA_DIR))


def _swap_into_place(tmp: str, out_base: str) -> None:
    """Replace out_base with the freshly built tmp tree via renames (near-atomic)."""
    old = out_base + ".old"
    if os.path.isdir(old):
        shutil.rmtree(old, ignore_errors=True)
    if os.path.exists(out_base):
        os.rename(out_base, old)
    os.rename(tmp, out_base)
    if os.path.isdir(old):
        shutil.rmtree(old, ignore_errors=True)


def ensure_generated(addon_id: str) -> str:
    """Return a scriptPath whose dialog XML is adapted to the active skin.

    EVERYTHING runs inside one try, and every fallback return uses `_safe_shipped`
    so the fallback itself cannot raise (this is what actually holds the "never
    break a dialog" invariant). The freshness check (getSkinDir + fontset +
    Font.xml mtime + marker read) runs per open; it is cheap (one RPC + a few
    stats) and generation happens only on a genuine cache miss. Identity skins
    (Estuary and any skin defining all anchor names) skip generation entirely and
    return the shipped path unchanged.

    The fallback is a RELIABILITY mechanism, not a security boundary: a
    successfully generated tree is always well-formed because parse_fontset
    allowlists font names.
    """
    try:
        if not _VALID_ID.match(addon_id or ""):
            log.warning("Rejected invalid addon_id", event="skinfont.bad_id",
                       addon=addon_id)
            return _safe_shipped(addon_id)
        addon = xbmcaddon.Addon(addon_id)          # inside try: a bad id -> fallback
        shipped = addon.getAddonInfo('path')
        skin_id, skin_version = _active_skin()
        fontset = _active_fontset()
        font_xml_path = _find_skin_font_xml()
        if not font_xml_path:
            return shipped                          # cannot adapt; shipped is valid
        skin_xml_dir = os.path.dirname(font_xml_path)
        mtimes = [os.path.getmtime(font_xml_path)]
        try:
            for entry in os.listdir(skin_xml_dir):
                if entry.lower().endswith(".xml"):
                    mtimes.append(os.path.getmtime(os.path.join(skin_xml_dir, entry)))
        except OSError:
            pass
        font_mtime = int(max(mtimes))
        key = cache_key(skin_id, skin_version, fontset,
                        addon.getAddonInfo('version'), font_mtime)

        out_base = xbmcvfs.translatePath(
            "special://profile/addon_data/%s/skingen" % addon_id)
        os.makedirs(os.path.dirname(out_base), exist_ok=True)
        marker = os.path.join(out_base, _MARKER)

        def _fresh() -> bool:
            try:
                with open(marker, "r", encoding="utf-8") as fh:
                    return fh.read().strip() == key
            except OSError:
                return False

        if _fresh():
            return out_base

        includes = _load_skin_includes(skin_xml_dir)
        with open(font_xml_path, "r", encoding="utf-8") as fh:
            font_map = build_font_map(parse_fontset(fh.read(), fontset, includes))
        if all(anchor == mapped for anchor, mapped in font_map.items()):
            return shipped                          # identity skin: no rewrite needed

        lock_path = out_base + ".lock"
        fd = _try_lock(lock_path)
        if fd is None:
            return shipped                          # another process building; do not block
        try:
            if _fresh():                            # built while we waited for the lock
                return out_base
            # The lock above is best-effort (see _try_lock's stale-reclaim). A
            # PID-unique temp dir makes a lock race benign: each builder writes
            # its own temp, output is identical for the same skin+fonts, and the
            # atomic rename-swap means a racing loser at worst falls back to the
            # shipped path for that one open.
            tmp = out_base + ".new." + str(os.getpid())
            if os.path.isdir(tmp):
                shutil.rmtree(tmp, ignore_errors=True)
            try:
                _generate_into(shipped, tmp, font_map)
                with open(os.path.join(tmp, _MARKER), "w", encoding="utf-8") as fh:
                    fh.write(key)
                _swap_into_place(tmp, out_base)
            except Exception:
                shutil.rmtree(tmp, ignore_errors=True)  # no partial tmp left behind
                raise
            log.info("Generated adapted dialog XML", event="skinfont.generate",
                     skin=skin_id, mapped=str(font_map))
        finally:
            _release_lock(fd, lock_path)
        return out_base
    except (OSError, ET.ParseError):
        log.warning("Font generation unavailable; using shipped path",
                    event="skinfont.fallback", addon=addon_id)
        return _safe_shipped(addon_id)
    except Exception:  # noqa: BLE001
        log.exception("Unexpected font generation error; using shipped path",
                      event="skinfont.error", addon=addon_id)
        return _safe_shipped(addon_id)
