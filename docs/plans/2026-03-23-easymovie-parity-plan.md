# EasyMovie UI Parity Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Port EasyMovie's dialog/browse UI refinements to EasyTV — skin guidelines, heading standardization, dialog upgrades, InfoTagVideo expansion, and a new PosterGrid browse mode.

**Architecture:** Five phases of incremental skin XML, Python, and documentation changes. Each phase is self-contained and shippable. TV-specific metadata density (episode counts, progress, last watched) means positions can't be copied directly from EasyMovie — layouts must accommodate more metadata rows.

**Tech Stack:** Kodi skin XML (WindowXMLDialog), Python 3.8+, Kodi 21+ InfoTagVideo API

**Design doc:** `docs/plans/2026-03-23-easymovie-parity-design.md`

---

## Phase 1: Guidelines & Includes.xml

### Task 1: Update skin-guidelines.md with descender padding rule

**Files:**
- Modify: `.claude/skin-guidelines.md` (after line 64, after "Usage Rules" section)

**Step 1: Add descender padding rule section**

After the Typography → Usage Rules section (line 64), add this new subsection:

```markdown
### Descender Padding Rule

Stacked labels must maintain a minimum **4px visual gap** to prevent descender overlap (letters like g, y, p). Calculate effective text bounds accounting for font centering within label height:

```
eff_bottom = top + (height + font_px) / 2
eff_top    = top + (height - font_px) / 2
gap        = next_eff_top - prev_eff_bottom    (must be >= 4px)
```

Font reference sizes: font10 ~21px, font12 ~24px, font13 ~30px, font14_title ~32px.
```

**Step 2: Verify**

Run: `cat .claude/skin-guidelines.md | grep -A5 "Descender Padding"`
Expected: The new section appears.

**Step 3: Commit**

```bash
git add .claude/skin-guidelines.md
git commit -m "docs: add descender padding rule to skin guidelines"
```

### Task 2: Add full-screen heading area standard to skin-guidelines.md

**Files:**
- Modify: `.claude/skin-guidelines.md` (after Dialog Heading Area section, before Typography)

**Step 1: Add full-screen heading section**

After the Dialog Heading Area section (line 49: "Content width = dialog width − (2 × 30)."), add:

```markdown
## Full-Screen Heading Area

Full-screen browse views (Posters, BigScreen, PosterGrid) use a separate standard:

| Property | Value | Notes |
|----------|-------|-------|
| Heading top | 15 | |
| Heading height | 40 | Room for font14_title |
| Count top | 20 | font10, right-aligned |
| Accent line top | 60 | 5px below heading bottom |
| Accent line height | 2 | |
| Content top | 72 | 10px below line |
| Side padding | 40 | BigScreen uses 80 for cinematic feel |
| Accent width | full usable width | |

Item count convention: `$INFO[Container(655).CurrentItem] / $INFO[Container(655).NumItems]`
```

**Step 2: Commit**

```bash
git add .claude/skin-guidelines.md
git commit -m "docs: add full-screen heading area standard to skin guidelines"
```

### Task 3: Fix Includes.xml separator texture

**Files:**
- Modify: `resources/skins/Default/1080i/Includes.xml:114`

**Step 1: Change separator texture**

At line 114, change:
```xml
<texture colordiffuse="$INFO[Window.Property(EasyTV.AccentGlow)]">common/white.png</texture>
```
to:
```xml
<texture colordiffuse="$INFO[Window.Property(EasyTV.AccentGlow)]">common/line_fade.png</texture>
```

**Step 2: Verify**

Run: `grep "line_fade" resources/skins/Default/1080i/Includes.xml`
Expected: The separator include now uses `line_fade.png`.

**Step 3: Commit**

```bash
git add resources/skins/Default/1080i/Includes.xml
git commit -m "fix(skin): use line_fade.png for separator include texture

Matches the skin guidelines which specify line_fade.png for all
separator/accent lines. Aligns with EasyMovie's Includes.xml."
```

---

## Phase 2: Browse View Heading Standardization

### Task 4: Standardize CardList heading area and add item count

**Files:**
- Modify: `resources/skins/Default/1080i/script-easytv-cardlist.xml`

**Current state:**
- Heading: top=13, height=40 (correct)
- Accent line: top=66 (already correct!)
- Info bar: top=82, height=25
- List: top=122, height=624

CardList already follows the dialog heading standard. Only change needed: add item count.

**Step 1: Add item count label**

After the heading label (line 77), before the accent line (line 80), add:

```xml
                <!-- Item count -->
                <control type="label">
                    <left>30</left>
                    <top>18</top>
                    <width>1340</width>
                    <height>30</height>
                    <align>right</align>
                    <font>font10</font>
                    <textcolor>FF888888</textcolor>
                    <label>$INFO[Container(655).CurrentItem] / $INFO[Container(655).NumItems]</label>
                </control>
```

**Step 2: Commit**

```bash
git add resources/skins/Default/1080i/script-easytv-cardlist.xml
git commit -m "feat(skin): add item count to CardList heading"
```

### Task 5: Standardize SplitView heading area and add item count

**Files:**
- Modify: `resources/skins/Default/1080i/script-easytv-splitlist.xml`

**Current state:**
- Heading: top=13, height=40 (correct)
- Accent line: top=46 (WRONG — should be 66)
- List: top=71, height=700

**Step 1: Fix accent line position and span**

Change the accent line from left panel only to full-width spanning both panels:
- Move from line 86-93 (inside left panel group) to after the left panel group closing tag (line 93), as a direct child of the content group
- Change `top` from 46 to 66
- Change `width` from 730 to 1340 (full content width)
- Change `left` to 30

**Step 2: Add item count label**

Inside the left panel heading group (after the heading label, line 83), add:

```xml
                    <!-- Item count -->
                    <control type="label">
                        <left>0</left>
                        <top>5</top>
                        <width>730</width>
                        <height>30</height>
                        <align>right</align>
                        <font>font10</font>
                        <textcolor>FF888888</textcolor>
                        <label>$INFO[Container(655).CurrentItem] / $INFO[Container(655).NumItems]</label>
                    </control>
```

**Step 3: Adjust list start and height**

Change list control (currently at top=71, height=700):
- `top` from 71 to 82
- `height` from 700 to 648 (compensate for 11px lower start, keep bottom edge aligned with buttons)

**Step 4: Descender padding check on right panel labels**

Verify all stacked labels in the right detail panel. Reference the design doc's constraint about TV metadata density — this panel has more rows than EasyMovie's equivalent.

Current right panel stack:
- Episode title: top=377, h=35, font13(~30px) → eff_bottom=409.5
- Genre+Duration: top=417, h=28, font10(~21px) → eff_top=420.5, gap=11px ✓
- On Deck/Watched: top=450, h=28, font10 → eff_top=453.5, gap from 441.5=12px ✓
- Last watched: top=483, h=28, font10 → eff_top=486.5, gap from 474.5=12px ✓
- Separator: top=521
- Plot: top=535

All gaps ≥ 4px. No fixes needed.

**Step 5: Commit**

```bash
git add resources/skins/Default/1080i/script-easytv-splitlist.xml
git commit -m "feat(skin): standardize SplitView heading area and add item count

Move accent line from top=46 to top=66 matching dialog heading standard.
Span accent line across both panels. Add item count display. Adjust list
start position to top=82."
```

### Task 6: Standardize Posters view heading area and add item count

**Files:**
- Modify: `resources/skins/Default/1080i/script-easytv-main.xml`

**Current state:** No heading area — just a left info panel starting at top=60 with fanart at top=0 (relative). No addon name heading, no accent line, no item count.

**Step 1: Add heading area above the two-column layout**

Before the left info panel group (line 37), add a heading group as a direct child of the main content group:

```xml
            <!-- ==================== HEADER ==================== -->

            <!-- Addon name heading -->
            <control type="label">
                <left>40</left>
                <top>15</top>
                <width>800</width>
                <height>40</height>
                <font>font14_title</font>
                <textcolor>$INFO[Window.Property(EasyTV.Accent)]</textcolor>
                <label>$INFO[Window.Property(EasyTV.AddonName)]</label>
            </control>

            <!-- Item count -->
            <control type="label">
                <left>40</left>
                <top>20</top>
                <width>1840</width>
                <height>30</height>
                <align>right</align>
                <font>font10</font>
                <textcolor>FF888888</textcolor>
                <label>$INFO[Container(655).CurrentItem] / $INFO[Container(655).NumItems]</label>
            </control>

            <!-- Accent line separator -->
            <control type="image">
                <left>40</left>
                <top>60</top>
                <width>1840</width>
                <height>2</height>
                <texture colordiffuse="$INFO[Window.Property(EasyTV.AccentGlow)]">common/line_fade.png</texture>
            </control>
```

**Step 2: Adjust left info panel position**

Change left info panel group top from 60 to 72 (content starts at 72 per full-screen heading standard). Adjust inner element positions if needed to maintain relative spacing.

**Step 3: Adjust poster grid position**

Change poster panel top from 40 to 72. Adjust height from 1000 to 968 (maintain bottom edge).

**Step 4: Descender padding check on left panel**

Current left panel stack (relative positions within group at top=60, will become top=72):
- Show title: top=369, h=45, font13(~30px) → eff_bottom=369+(45+30)/2=406.5
- Episode title: top=419, h=30, font12(~24px) → eff_top=419+(30-24)/2=422, gap=15.5px ✓
- Genre+Duration: top=454, h=28, font10(~21px) → eff_top=454+3.5=457.5, gap from 443=14.5px ✓
- Episode/Progress: top=487, gap from 475.5=15px ✓
- On Deck/Watched: top=520, gap from 508.5=15px ✓
- Last Watched: top=553, gap from 541.5=15px ✓

All gaps fine.

**Step 5: Commit**

```bash
git add resources/skins/Default/1080i/script-easytv-main.xml
git commit -m "feat(skin): add heading area to Posters view

Add addon name, item count, and accent line following the full-screen
heading standard. Adjust content positions to start at top=72."
```

### Task 7: Standardize BigScreen view heading area and add item count

**Files:**
- Modify: `resources/skins/Default/1080i/script-easytv-BigScreenList.xml`

**Current state:** Has an info bar at top=30 with metadata, but no heading label, no accent line, no item count. Metadata is all on one long line.

**Step 1: Add heading area**

Replace the current info bar (lines 24-33) with a proper heading area:

```xml
        <!-- ==================== HEADER ==================== -->

        <!-- Addon name heading -->
        <control type="label">
            <left>80</left>
            <top>15</top>
            <width>800</width>
            <height>40</height>
            <font>font14_title</font>
            <textcolor>$INFO[Window.Property(EasyTV.Accent)]</textcolor>
            <label>$INFO[Window.Property(EasyTV.AddonName)]</label>
        </control>

        <!-- Item count -->
        <control type="label">
            <left>80</left>
            <top>20</top>
            <width>1760</width>
            <height>30</height>
            <align>right</align>
            <font>font10</font>
            <textcolor>FF888888</textcolor>
            <label>$INFO[Container(655).CurrentItem] / $INFO[Container(655).NumItems]</label>
        </control>

        <!-- Accent line separator -->
        <control type="image">
            <left>80</left>
            <top>60</top>
            <width>1760</width>
            <height>2</height>
            <texture colordiffuse="$INFO[Window.Property(EasyTV.AccentGlow)]">common/line_fade.png</texture>
        </control>

        <!-- Info bar (metadata for focused item) -->
        <control type="label">
            <left>80</left>
            <top>72</top>
            <width>1760</width>
            <height>25</height>
            <font>font10</font>
            <textcolor>FFAAAAAA</textcolor>
            <label>[COLOR $INFO[Window.Property(EasyTV.Accent)]]$INFO[Container(655).ListItem.Property(episodeno)][/COLOR]  •  $ADDON[script.easytv 32222]  [COLOR $INFO[Window.Property(EasyTV.Accent)]]$INFO[Container(655).ListItem.Property(percentplayed)][/COLOR]  •  $ADDON[script.easytv 32223] [COLOR $INFO[Window.Property(EasyTV.Accent)]]$INFO[Container(655).ListItem.Property(numondeck)][/COLOR]  •  $ADDON[script.easytv 32224] [COLOR $INFO[Window.Property(EasyTV.Accent)]]$INFO[Container(655).ListItem.Property(numwatched)][/COLOR]  •  $ADDON[script.easytv 32225] [COLOR $INFO[Window.Property(EasyTV.Accent)]]$INFO[Container(655).ListItem.Property(numskipped)][/COLOR]  •  $ADDON[script.easytv 32065] [COLOR $INFO[Window.Property(EasyTV.Accent)]]$INFO[Container(655).ListItem.Property(lastwatched)][/COLOR]  •  $INFO[Container(655).ListItem.Property(genre),[, ]]$INFO[Container(655).ListItem.Property(duration),  •  ~,/ep]</label>
        </control>
```

**Step 2: Adjust content positions**

The main content group currently starts at top=75 for the fanart. With the new header taking space through top=97 (info bar ends), adjust:
- Fanart group top from 75 to 105
- Episode list top from 80 to 105
- Adjust list height to compensate

**Step 3: Commit**

```bash
git add resources/skins/Default/1080i/script-easytv-BigScreenList.xml
git commit -m "feat(skin): add heading area to BigScreen view

Add addon name, item count, accent line, and metadata bar following
the full-screen heading standard with 80px cinematic padding."
```

---

## Phase 3: Dialog Refinements

### Task 8: Create missed episode warning dialog XML

**Files:**
- Create: `resources/skins/Default/1080i/script-easytv-missedwarning.xml`

**Step 1: Create the XML**

Create `script-easytv-missedwarning.xml` modeled on EasyMovie's `script-easymovie-setwarning.xml` (800x480 dialog with poster). Use EasyTV property names (`EasyTV.Accent` etc.) and control IDs matching `CountdownDialog`: 1 (heading), 2 (message), 4 (subtitle), 10 (yes), 11 (no), 20 (poster).

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!--
    EasyTV Missed Episode Warning Dialog
    Resolution: 1080i (1920x1080)

    Shown when a user plays a later episode than the stored next episode.
    No countdown timer.

    Control IDs:
        1  - Heading label
        2  - Message label (primary — show/episode info, up to 5 lines)
        4  - Subtitle label (centered question)
        10 - Yes/primary button (play stored episode)
        11 - No/secondary button (continue current)
        20 - Show poster image
-->
<window>
    <zorder>1</zorder>
    <defaultcontrol always="true">10</defaultcontrol>

    <controls>
        <!-- Dim overlay -->
        <control type="image">
            <left>0</left>
            <top>0</top>
            <width>1920</width>
            <height>1080</height>
            <texture colordiffuse="BB000000">common/white.png</texture>
            <animation type="WindowOpen" reversible="false">
                <effect type="fade" start="0" end="100" time="300" />
            </animation>
            <animation type="WindowClose" reversible="false">
                <effect type="fade" start="100" end="0" time="300" />
            </animation>
        </control>

        <!-- Dialog Container: 800x480 centered -->
        <control type="group">
            <left>560</left>
            <top>300</top>
            <width>800</width>
            <height>480</height>
            <animation type="WindowOpen" reversible="false">
                <effect type="fade" start="0" end="100" time="300" delay="100" />
                <effect type="slide" start="0,-100" end="0" center="auto" tween="back" easing="out" time="600" delay="100" />
            </animation>
            <animation type="WindowClose" reversible="false">
                <effect type="zoom" start="100" end="95" center="auto" tween="sine" easing="out" time="300" />
                <effect type="fade" start="100" end="0" tween="cubic" easing="out" time="300" />
            </animation>

            <!-- Accent border frame -->
            <control type="image">
                <left>-2</left>
                <top>-2</top>
                <width>804</width>
                <height>484</height>
                <texture border="12" colordiffuse="$INFO[Window.Property(EasyTV.Accent)]">common/white_rounded.png</texture>
            </control>

            <!-- Rounded dark panel background -->
            <control type="image">
                <left>0</left>
                <top>0</top>
                <width>800</width>
                <height>480</height>
                <texture border="12">common/menu.png</texture>
                <colordiffuse>ffffffff</colordiffuse>
            </control>

            <!-- Heading Label (ID 1) -->
            <control type="label" id="1">
                <left>30</left>
                <top>13</top>
                <width>740</width>
                <height>40</height>
                <align>center</align>
                <textcolor>$INFO[Window.Property(EasyTV.Accent)]</textcolor>
                <font>font14_title</font>
                <label></label>
            </control>

            <!-- Accent line separator -->
            <control type="image">
                <left>30</left>
                <top>66</top>
                <width>740</width>
                <height>2</height>
                <texture colordiffuse="$INFO[Window.Property(EasyTV.AccentGlow)]">common/line_fade.png</texture>
            </control>

            <!-- Show Poster (ID 20) -->
            <control type="image" id="20">
                <left>30</left>
                <top>82</top>
                <width>160</width>
                <height>240</height>
                <aspectratio>keep</aspectratio>
                <texture background="true">-</texture>
            </control>

            <!-- Message (ID 2) — show/episode info, up to 5 lines -->
            <control type="label" id="2">
                <left>210</left>
                <top>85</top>
                <width>560</width>
                <height>165</height>
                <align>left</align>
                <textcolor>ffFFFFFF</textcolor>
                <font>font13</font>
                <wrapmultiline>true</wrapmultiline>
                <label>-</label>
            </control>

            <!-- Subtitle (ID 4) — centered question -->
            <control type="label" id="4">
                <left>30</left>
                <top>340</top>
                <width>740</width>
                <height>50</height>
                <align>center</align>
                <textcolor>FFAAAAAA</textcolor>
                <font>font12</font>
                <wrapmultiline>true</wrapmultiline>
                <label>-</label>
            </control>

            <!-- Button Row -->
            <control type="group">
                <left>185</left>
                <top>415</top>
                <width>430</width>
                <height>50</height>

                <!-- Yes/primary Button (ID 10) -->
                <control type="button" id="10">
                    <left>0</left>
                    <top>0</top>
                    <width>200</width>
                    <height>50</height>
                    <align>center</align>
                    <aligny>center</aligny>
                    <font>font12</font>
                    <textoffsetx>10</textoffsetx>
                    <textcolor>FFFFFFFF</textcolor>
                    <focusedcolor>$INFO[Window.Property(EasyTV.ButtonTextFocused)]</focusedcolor>
                    <onright>11</onright>
                    <onleft>11</onleft>
                    <texturefocus border="12" colordiffuse="$INFO[Window.Property(EasyTV.ButtonFocus)]">common/white_rounded.png</texturefocus>
                    <texturenofocus border="12" colordiffuse="1fFFFFFF">common/white_rounded.png</texturenofocus>
                </control>

                <!-- No/secondary Button (ID 11) -->
                <control type="button" id="11">
                    <left>230</left>
                    <top>0</top>
                    <width>200</width>
                    <height>50</height>
                    <align>center</align>
                    <aligny>center</aligny>
                    <font>font12</font>
                    <textoffsetx>10</textoffsetx>
                    <textcolor>FFFFFFFF</textcolor>
                    <focusedcolor>$INFO[Window.Property(EasyTV.ButtonTextFocused)]</focusedcolor>
                    <onright>10</onright>
                    <onleft>10</onleft>
                    <texturefocus border="12" colordiffuse="$INFO[Window.Property(EasyTV.ButtonFocus)]">common/white_rounded.png</texturefocus>
                    <texturenofocus border="12" colordiffuse="1fFFFFFF">common/white_rounded.png</texturenofocus>
                </control>
            </control>
        </control>
    </controls>
</window>
```

**Step 2: Descender padding verification**

- Heading: top=13, h=40, font14_title(~32px) → eff_bottom=13+(40+32)/2=49
- Accent line: top=66, gap=17px ✓ (non-text separator)
- Message: top=85, h=165, font13(~30px) — multiline, no stacking issue
- Subtitle: top=340, h=50, font12(~24px) → eff_bottom=340+(50+24)/2=377
- Buttons: top=415, gap=38px ✓

All clear.

**Step 3: Commit**

```bash
git add resources/skins/Default/1080i/script-easytv-missedwarning.xml
git commit -m "feat(skin): add missed episode warning dialog with poster

New 800x480 dialog for missed episode warnings, showing the show
poster alongside episode info. Matches EasyMovie's set warning dialog
pattern. Uses CountdownDialog control IDs for Python reuse."
```

### Task 9: Update playback_monitor.py to use missed warning dialog

**Files:**
- Modify: `resources/lib/service/playback_monitor.py:343-408` (`_check_previous_episode` method)

**Step 1: Replace show_confirm with CountdownDialog**

In `_check_previous_episode()`, replace the current `show_confirm` call (lines 385-388) with a `CountdownDialog` using the new XML:

Change from:
```python
from resources.lib.ui.dialogs import show_confirm
msg = (lang(32161) % (showtitle, stored_seas, stored_epis)) + '\n' + lang(32162)
source_addon_id = self._window.getProperty(PROP_SOURCE_ADDON_ID) or None
dialog_result = show_confirm(lang(32160), msg, addon_id=source_addon_id)
```

To:
```python
from resources.lib.ui.dialogs import CountdownDialog

source_addon_id = self._window.getProperty(PROP_SOURCE_ADDON_ID) or None
source_addon = xbmcaddon.Addon(source_addon_id) if source_addon_id else xbmcaddon.Addon()
addon_path = source_addon.getAddonInfo('path')
heading = source_addon.getAddonInfo('name')

# Get show poster
poster = self._window.getProperty(
    "EasyTV.%s.Art(tvshow.poster)" % show_id
)

msg = lang(32161) % (showtitle, stored_seas, stored_epis)
subtitle = lang(32162)

dlg = CountdownDialog(
    'script-easytv-missedwarning.xml', addon_path, 'Default',
    message=msg,
    subtitle=subtitle,
    yes_label=lang(32078),   # "Yes"
    no_label=lang(32079),    # "No"
    duration=0,              # No timer
    heading=heading,
    poster=poster,
    addon_id=source_addon_id,
)
dlg.doModal()
dialog_result = dlg.result
del dlg
```

**Step 2: Verify syntax**

Run: `python3 -m py_compile resources/lib/service/playback_monitor.py && echo "OK"`
Expected: `OK`

**Step 3: Commit**

```bash
git add resources/lib/service/playback_monitor.py
git commit -m "feat: upgrade missed episode warning to poster dialog

Use CountdownDialog with the new missedwarning XML instead of basic
show_confirm. Shows the show poster alongside episode information
for a richer user experience matching EasyMovie's set warning."
```

### Task 10: Fix next episode dialog message font

**Files:**
- Modify: `resources/skins/Default/1080i/script-easytv-nextepisode.xml:109`

**Step 1: Change font**

At line 109, change:
```xml
<font>font14_title</font>
```
to:
```xml
<font>font13</font>
```

Typography rule: `font14_title` is for headings only; body message text uses `font13`.

**Step 2: Descender padding check**

- Heading: top=13, h=40, font14_title → eff_bottom=49 (then accent line at 66) ✓
- Message (ID 2): top=145, h=60, font13(~30px) → eff_bottom=145+(60+30)/2=190
- Subtitle (ID 4): top=210, h=25, font10(~21px) → eff_top=210+(25-21)/2=212, gap=22px ✓
- Buttons: top=330, gap from subtitle eff_bottom(210+23=233)=97px ✓

All clear.

**Step 3: Commit**

```bash
git add resources/skins/Default/1080i/script-easytv-nextepisode.xml
git commit -m "fix(skin): use font13 for next episode dialog message

font14_title is reserved for headings per typography guidelines.
Body message text should use font13."
```

### Task 11: Descender padding audit on all remaining dialog XMLs

**Files:**
- Review: `resources/skins/Default/1080i/script-easytv-confirm.xml`
- Review: `resources/skins/Default/1080i/script-easytv-countdown.xml`
- Review: `resources/skins/Default/1080i/script-easytv-select.xml`
- Review: `resources/skins/Default/1080i/script-easytv-showselector.xml`
- Review: `resources/skins/Default/1080i/script-easytv-contextwindow.xml`

**Step 1: Audit each dialog**

For each dialog XML, identify all stacked label pairs and verify the descender gap formula. Document any violations.

**Step 2: Fix any violations found**

Adjust `top` values for any gaps < 4px.

**Step 3: Commit (only if fixes were needed)**

```bash
git add resources/skins/Default/1080i/
git commit -m "fix(skin): correct descender padding in dialog XMLs"
```

---

## Phase 4: InfoTagVideo Expansion

### Task 12: Expand InfoTagVideo fields in browse_window.py

**Files:**
- Modify: `resources/lib/ui/browse_window.py:218-293` (`_create_list_item` method)

**Step 1: Add InfoTagVideo fields**

After the existing `info_tag.setTitle(eptitle)` line (line 291), add:

```python
        # Additional InfoTagVideo fields from service window properties
        year_str = WINDOW.getProperty(f"{prop_prefix}.Year")
        if year_str:
            try:
                info_tag.setYear(int(year_str))
            except ValueError:
                pass

        genre_str = WINDOW.getProperty(f"{prop_prefix}.Genre")
        if genre_str:
            info_tag.setGenres([g.strip() for g in genre_str.split(',')])

        if duration_secs:
            try:
                info_tag.setDuration(int(duration_secs))
            except ValueError:
                pass
```

Note: `year_str` comes from `EasyTV.{show_id}.Year` (set by daemon.py:1202). `genre_str` comes from `EasyTV.{show_id}.Genre` (set by daemon.py:1204). `duration_secs` is already read at line 248 as `WINDOW.getProperty(f"{prop_prefix}.Duration")`.

**Step 2: Add the same to _update_list_item**

In `_update_list_item()` (line 295+), add the same InfoTagVideo fields after the existing `info_tag.setTitle(eptitle)`:

```python
        year_str = WINDOW.getProperty(f"{prop_prefix}.Year")
        if year_str:
            try:
                info_tag.setYear(int(year_str))
            except ValueError:
                pass

        genre_str = WINDOW.getProperty(f"{prop_prefix}.Genre")
        if genre_str:
            info_tag.setGenres([g.strip() for g in genre_str.split(',')])

        if duration_secs:
            try:
                info_tag.setDuration(int(duration_secs))
            except ValueError:
                pass
```

**Step 3: Verify syntax**

Run: `python3 -m py_compile resources/lib/ui/browse_window.py && echo "OK"`
Expected: `OK`

**Step 4: Run pyflakes**

Run: `pyflakes resources/lib/ui/browse_window.py`
Expected: No errors

**Step 5: Commit**

```bash
git add resources/lib/ui/browse_window.py
git commit -m "feat: expand InfoTagVideo fields in browse ListItems

Set year, genres, and duration via InfoTagVideo for browse window
ListItems. These are now accessible in skin XML as ListItem.Year,
ListItem.Genre, ListItem.Duration. Data comes from existing service
window properties — no service changes needed."
```

---

## Phase 5: PosterGrid View

### Task 13: Copy scrim asset from EasyMovie

**Files:**
- Create: `resources/skins/Default/media/common/scrim_topleft.png` (copy from EasyMovie)

**Step 1: Copy the asset**

```bash
cp /home/martijn/script.easymovie/resources/skins/Default/media/common/scrim_topleft.png \
   /home/martijn/script.easytv/resources/skins/Default/media/common/scrim_topleft.png
```

**Step 2: Commit**

```bash
git add resources/skins/Default/media/common/scrim_topleft.png
git commit -m "art: add scrim overlay for poster grid watched badge"
```

### Task 14: Add VIEW_POSTER_GRID constant and settings option

**Files:**
- Modify: `resources/lib/constants.py` (near existing view style usage or at end of constants section)
- Modify: `resources/lib/ui/browse_window.py:609-615` (`get_skin_xml_file`)
- Modify: `resources/settings.xml:242-254` (view_style setting options)
- Modify: `resources/language/resource.language.en_gb/strings.po` (add "Showcase" label)

**Step 1: Add string for Showcase**

Add to `strings.po` after the last entry (32746):

```po
msgctxt "#32747"
msgid "Showcase"
msgstr ""
```

EasyMovie uses "Showcase" (string 32522) for this view — matching sibling vocabulary.

**Step 2: Add to settings.xml**

In the view_style setting options (line 248-253), add before the closing `</options>`:

```xml
                            <option label="32747">4</option>
```

**Step 3: Update get_skin_xml_file()**

In `browse_window.py`, update the skins dict (lines 609-614):

```python
    skins = {
        0: "script-easytv-cardlist.xml",
        1: "script-easytv-main.xml",
        2: "script-easytv-BigScreenList.xml",
        3: "script-easytv-splitlist.xml",
        4: "script-easytv-postergrid.xml",
    }
```

**Step 4: Verify**

Run: `python3 -m py_compile resources/lib/ui/browse_window.py && echo "OK"`
Expected: `OK`

**Step 5: Commit**

```bash
git add resources/lib/constants.py resources/lib/ui/browse_window.py \
       resources/settings.xml resources/language/resource.language.en_gb/strings.po
git commit -m "feat: add Showcase (PosterGrid) as 5th browse view option

Add view style 4 with 'Showcase' label matching EasyMovie sibling
vocabulary. Wire up settings, constants, and skin XML mapping."
```

### Task 15: Create PosterGrid XML

**Files:**
- Create: `resources/skins/Default/1080i/script-easytv-postergrid.xml`

**Step 1: Create the XML**

Create `script-easytv-postergrid.xml` modeled on EasyMovie's `script-easymovie-postergrid.xml` but with TV show metadata in the info panel.

Key adaptations from EasyMovie:
- Replace `EasyMovie.*` property names with `EasyTV.*`
- Replace movie metadata (year/MPAA/rating/runtime/genre/collection) with TV metadata:
  - Show title (font13, Accent)
  - Episode code + episode title (font10, white)
  - Genre · ~Duration/ep (font10, FFAAAAAA)
  - On Deck / Watched / Skipped counts (font10, FFAAAAAA with Accent values)
  - Last Watched (font10, FFAAAAAA with Accent value)
- Replace movie set badge with watched-only badge (no set concept for TV)
- Use `ListItem.Art(thumb)` for poster (same as existing Posters view)
- Use `ListItem.Property(Fanart_Image)` is NOT used — PosterGrid has no fanart display
- Plot uses `ListItem.Plot` via textbox on right side
- Control ID 655 for the fixedlist (matches all other views)
- No buttons (context menu handles actions, matching BigScreen/Posters approach)

Full-screen heading standard: heading top=15, accent line top=60, content top=72, side padding=40.

Filmstrip: horizontal fixedlist with focusposition=1.
- Unfocused: 210px wide cells, poster 182x273 at (14, 258)
- Focused: 440px wide cells, poster 420x630 at (10, 80) with accent border and zoom animation
- Watched scrim + icon overlay on poster corner

Info panel below filmstrip (at ~870px):
- Left (40px): Show title, episode info, genre, counts, last watched
- Right (800px): Plot textbox

The exact XML should closely follow EasyMovie's `script-easymovie-postergrid.xml` structure (already read above) with the TV-specific metadata substitutions listed.

**Step 2: Descender padding verification on info panel**

Verify all stacked labels in the info panel follow the 4px minimum gap rule. Use the font reference sizes and the formula from the design doc.

**Step 3: Commit**

```bash
git add resources/skins/Default/1080i/script-easytv-postergrid.xml
git commit -m "feat(skin): add Showcase (PosterGrid) browse view

Full-screen horizontal poster filmstrip with focused zoom animation.
TV-specific info panel with episode code, genre, on deck/watched/
skipped counts, last watched date, and plot. Follows full-screen
heading standard with addon name, item count, and accent line."
```

### Task 16: Final validation

**Step 1: Run full verification**

```bash
find . -name "*.py" -not -path "*/__pycache__/*" \
  -exec python3 -m py_compile {} \; && \
echo "Syntax OK" && \
pyflakes $(find . -name "*.py" -not -path "*/__pycache__/*")
```

**Step 2: Run pyright**

```bash
pyright
```

**Step 3: Run kodi-addon-checker**

```bash
kodi-addon-checker --branch omega .
```

**Step 4: Commit any fixes if needed**

---

## Summary

| Phase | Tasks | Key Files |
|-------|-------|-----------|
| 1: Guidelines | 1-3 | `.claude/skin-guidelines.md`, `Includes.xml` |
| 2: Headings | 4-7 | All 4 browse view XMLs |
| 3: Dialogs | 8-11 | `missedwarning.xml`, `nextepisode.xml`, `playback_monitor.py` |
| 4: InfoTagVideo | 12 | `browse_window.py` |
| 5: PosterGrid | 13-16 | `postergrid.xml`, `constants.py`, `browse_window.py`, `settings.xml`, `strings.po` |
