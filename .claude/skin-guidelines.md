# EasyTV Skin & Dialog Design Guidelines

All custom UI is rendered via Kodi `WindowXMLDialog`. These guidelines ensure visual consistency across all EasyTV dialogs and browse views.

## UX Principles

1. **Design for 10-foot readability first** — all primary content must be legible from a couch, not just in screenshots
2. **Make focus state unmissable** — the user must instantly know which item is selected at all times
3. **Keep browse views scan-friendly** — prioritize quick comparison and decision-making over long-form reading
4. **Humanize computed data** — no raw decimals or system-internal formats; use "Today", "2 days", not "0.0 days"
5. **Group metadata by meaning** — episode-level, show-level, and status-level data should not visually blur together
6. **Let mode purpose drive layout** — dense modes optimize for speed; artwork-driven modes optimize for recognition

## Browse Mode Intent

| Mode | Purpose | Optimized for |
|------|---------|---------------|
| Split View | Balanced browsing with context | Confidence and comfort, general audiences |
| Big Screen | Immersive artwork-first | Small curated sets, mood browsing |
| Poster | Visual recognition by cover art | Medium lists, recognition-based browsing |
| Card List | Fast data-dense browsing | Large lists, power users |

## Content Formatting Rules

| Data | Format | Example |
|------|--------|---------|
| Relative time | No decimals; "Today" / "X days" / "Never" | "Today", "3 days", "Never" |
| Episode codes | Uppercase `SXXEXX` in compact views | `S01E01`, `S02E14` |
| Episode detail | `Season X • Episode Y` in detail panels | `Season 2 • Episode 1` |
| Plot label | "Plot" without ellipsis | `Plot  [plot text]` |
| Empty metadata | Collapse cleanly, don't show "0" or blank labels | |

## Dialog Heading Area

Every dialog with a title uses this standardized layout:

| Property | Value | Notes |
|----------|-------|-------|
| Heading top | 13 | Visually centered between top edge and accent line |
| Heading height | 40 | Room for font14_title |
| Heading font | `font14_title` | |
| Heading color | `$INFO[Window.Property(EasyTV.Accent)]` | Theme accent |
| Accent line top | 66 | 6px below heading bottom |
| Accent line height | 2 | |
| Accent line texture | `common/line_fade.png` | colordiffuse=AccentGlow |
| Content top | 82 | 14px below line |
| Side padding | 30 | Left/right inset for heading and line |

Content width = dialog width − (2 × 30).

## Typography

| Role | Font | Size class | Usage |
|------|------|-----------|-------|
| Heading | `font14_title` | Large, bold | Dialog headings, "EasyTV" title |
| Title | `font13` | Large | Show title in detail panels, episode title in detail |
| Body | `font12` | Medium | List item primary labels, plot text, buttons |
| Metadata | `font10` | Small | Stats, episode numbers, timestamps, secondary labels |

### Usage Rules
- Headings are always Accent color
- Body text in focused rows stays `font12` — do NOT upsize to `font13` on focus (causes layout shift)
- Metadata should be readable at TV distance; `font10` is the minimum usable size
- Plot/synopsis always uses `font12` (Body), never `font10`

### Descender Padding Rule

Stacked labels must maintain a minimum **4px visual gap** to prevent descender overlap (letters like g, y, p). Calculate effective text bounds accounting for font centering within label height:

```
eff_bottom = top + (height + font_px) / 2
eff_top    = top + (height - font_px) / 2
gap        = next_eff_top - prev_eff_bottom    (must be >= 4px)
```

Font reference sizes: font10 ~21px, font12 ~24px, font13 ~30px, font14_title ~32px.

## Color System

Colors are set as window properties by `apply_theme()` in `resources/lib/ui/__init__.py`. Theme definitions live in `THEME_COLORS` in `resources/lib/constants.py`.

| Property | Usage |
|----------|-------|
| `EasyTV.Accent` | Heading text, focused list text, checkmarks, poster borders |
| `EasyTV.AccentGlow` | Accent line separator |
| `EasyTV.AccentBG` | Focused list item background (semi-transparent) |
| `EasyTV.ButtonTextFocused` | Button text when focused |
| `EasyTV.ButtonFocus` | Button background when focused |

### Theme Color Values

```
                  Accent      ButtonFocus   AccentGlow    AccentBG        ButtonTextFocused
Golden Hour       FFF5A623    FFD4912A      FFF5C564      59B4781E        FF0D1117
Ultraviolet       FFA78BFA    FF7C3AED      FFC4B5FD      596432B4        FFFFFFFF
Ember             FFF87171    FFEF4444      FFFCA5A5      59B43232        FFFFFFFF
Nightfall         FF60A5FA    FF3B82F6      FF93C5FD      59286AB4        FFFFFFFF
```

Golden Hour uses dark button text (amber is bright); the others use white.

### Semantic Text Colors

| Role | Color | Usage |
|------|-------|-------|
| TextPrimary (unfocused) | `FFCCCCCC` | Show title, main labels, plot text |
| TextSecondary | `FFAAAAAA` | Stat labels, episode titles, episode numbers, subtitle text |
| TextTertiary | `FF888888` | Timestamps, progress percentage, least-important metadata |
| TextOnFocus | `ffFFFFFF` | All non-primary text in focused rows |
| TextAccent | Accent property | Primary label in focused rows, headings |

### Other Hard-Coded Colors

| Color | Usage |
|-------|-------|
| `BB000000` | Dim overlay behind dialogs |
| `0cffffff` | SurfaceSubtle — unfocused row background tint |
| `1fFFFFFF` | Unfocused button/control background |
| `44FFFFFF` | Unfocused unchecked checkbox |
| `66FFFFFF` | Focused unchecked checkbox |

## Icon Design

Icons live in `resources/skins/Default/media/`. They are drawn as **solid black on transparent** and colored at runtime via `colordiffuse`.

### Rendering Specs

| Property | Value |
|----------|-------|
| Canvas size | 256×256 (render), 64×64 (final) |
| Antialiasing | Render at 4× then downsample with LANCZOS |
| Color | Solid black `(0,0,0,255)` on transparent |
| Runtime coloring | `colordiffuse` (white for unfocused, accent or white for focused) |
| Display size in layouts | 16–20px depending on context |

### Rounded Box Container

Metadata icons (calendar, progress) use a rounded box matching the checkbox style:

| Property | Value (at 256px) |
|----------|-----------------|
| Box padding from canvas edge | 12px |
| Corner radius | 44px |
| Stroke width | 12px |
| Inner content area | ~120×120px centered |

### Existing Icons

| File | Shape | Usage |
|------|-------|-------|
| `check_on.png` | Checkmark | Multiselect selected state |
| `check_off.png` | Rounded box outline | Multiselect unselected state |
| `IconWatched.png` | Eye | Watched/selected indicator |

## Button Styling

```xml
<control type="button" id="ID">
    <width>200</width>
    <height>50</height>
    <align>center</align>
    <aligny>center</aligny>
    <font>font12</font>
    <textoffsetx>10</textoffsetx>
    <textcolor>FFFFFFFF</textcolor>
    <focusedcolor>$INFO[Window.Property(EasyTV.ButtonTextFocused)]</focusedcolor>
    <texturefocus border="12" colordiffuse="$INFO[Window.Property(EasyTV.ButtonFocus)]">common/white_rounded.png</texturefocus>
    <texturenofocus border="12" colordiffuse="1fFFFFFF">common/white_rounded.png</texturenofocus>
</control>
```

## Separator Lines

All separator/accent lines use `common/line_fade.png` with `colordiffuse=AccentGlow` — never `common/white.png` for separators (hard edges look wrong against the dark panel background).

```xml
<control type="image">
    <left>0</left>
    <top>VALUE</top>
    <width>VALUE</width>
    <height>2</height>
    <texture colordiffuse="$INFO[Window.Property(EasyTV.AccentGlow)]">common/line_fade.png</texture>
</control>
```

## List Items

- `itemlayout` and `focusedlayout` **MUST** have the same height (prevents row shift on focus)
- Focused and unfocused layouts must use **identical positions, fonts, and sizes** — only colors and background change. This prevents visual shifting when focus moves between rows.
- All labels must include `<aligny>center</aligny>` for vertical centering

### Focused Row Colors

| Element | Color | Notes |
|---------|-------|-------|
| Background | AccentBG | Semi-transparent accent fill |
| Primary label (show title) | Accent | Draws the eye to the show name |
| All other text (episode info, stats, timestamps) | `ffFFFFFF` | White — elevated from grey for readability |

### Unfocused Row Colors

| Element | Color | Notes |
|---------|-------|-------|
| Background | none (or `0cffffff` for card-style) | Subtle row distinction |
| Primary label | `FFCCCCCC` | |
| Secondary labels | `FFAAAAAA` (TextSecondary) | Episode titles, episode numbers |
| Tertiary labels | `FF888888` (TextTertiary) | Timestamps, progress percentage |

### fixedlist Exception

`fixedlist` with `focusposition` may use different heights for an expand-on-focus effect (focused row reveals additional info like episode title). The pinned focus position makes this smooth rather than jarring. This is the only acceptable exception to the "same height" rule.

## Dialog Structure

Every dialog follows this structure:

```xml
<window>
    <zorder>1</zorder>
    <defaultcontrol always="true">BUTTON_ID</defaultcontrol>

    <controls>
        <!-- 1. Dim overlay (1920x1080) -->
        <control type="image">
            <left>0</left><top>0</top>
            <width>1920</width><height>1080</height>
            <texture colordiffuse="BB000000">common/white.png</texture>
            <!-- fade in/out animations -->
        </control>

        <!-- 2. Dialog container group -->
        <control type="group">
            <!-- bounce/zoom animations (inlined) -->

            <!-- 3. Accent border frame (2px larger on each side) -->
            <control type="image">
                <left>-2</left><top>-2</top>
                <width>W+4</width><height>H+4</height>
                <texture border="12" colordiffuse="$INFO[Window.Property(EasyTV.Accent)]">common/white_rounded.png</texture>
            </control>

            <!-- 4. Dark background -->
            <control type="image">
                <width>W</width><height>H</height>
                <texture border="12">common/menu.png</texture>
                <colordiffuse>ffffffff</colordiffuse>
            </control>

            <!-- 5. Heading (standardized layout above) -->
            <!-- 6. Accent line -->
            <!-- 7. Content area (starts at top=82) -->
            <!-- 8. Buttons -->
        </control>
    </controls>
</window>
```

## Animation Recipes

All animations must be **inlined** — `<include>` tags don't resolve in WindowXMLDialog.

### Dialog open (bounce in)
```xml
<animation type="WindowOpen" reversible="false">
    <effect type="fade" start="0" end="100" time="300" delay="100" />
    <effect type="slide" start="0,-100" end="0" center="auto" tween="back" easing="out" time="600" delay="100" />
</animation>
```

### Dialog close (shrink out)
```xml
<animation type="WindowClose" reversible="false">
    <effect type="zoom" start="100" end="95" center="auto" tween="sine" easing="out" time="300" />
    <effect type="fade" start="100" end="0" tween="cubic" easing="out" time="300" />
</animation>
```

### Dim overlay fade in
```xml
<animation type="WindowOpen" reversible="false">
    <effect type="fade" start="0" end="100" time="300" />
</animation>
```

### Dim overlay fade out
```xml
<animation type="WindowClose" reversible="false">
    <effect type="fade" start="100" end="0" time="300" />
</animation>
```

### Browse view open (zoom in)
```xml
<animation type="WindowOpen" reversible="false">
    <effect type="fade" start="0" end="100" time="300" tween="sine" easing="in" />
    <effect type="zoom" start="85" end="100" time="300" center="auto" tween="sine" easing="out" />
</animation>
```

### Browse view close (zoom out)
```xml
<animation type="WindowClose" reversible="false">
    <effect type="zoom" start="100" end="85" center="auto" tween="sine" easing="out" time="300" />
    <effect type="fade" start="100" end="0" tween="cubic" easing="out" time="300" />
</animation>
```

### Animation Intent

| Context | Style | Why |
|---------|-------|-----|
| Dialogs (confirm, countdown, next episode) | Bounce in, shrink out (~700ms) | Infrequent modals — theatrical entrance draws attention |
| Browse views (all 4 modes) | Zoom in/out (300ms) | Frequent navigation — fast and light to avoid fatigue |
| Dim overlay | Fade (300ms) | Ambient — should not draw attention |
| Poster focus (Poster View) | Subtle zoom pulse (150ms) | Selection feedback — micro-interaction |

Principle: Animation speed should be inversely proportional to how often the user triggers it. Repeated actions (browse switching) should be fast. Rare events (dialog prompts) can be more expressive.

## Reserved Kodi Control IDs

These IDs are intercepted by Kodi's internal CGUIWindow and **must not** be used for custom buttons:

| ID | Kodi usage | Impact |
|----|-----------|--------|
| 2 | View mode | onClick still fires but may have side effects |
| 3 | Sort by | **onClick never fires** — fully intercepted |
| 4 | Sort order | Intercepted |

**Safe range:** Use IDs 5+ for buttons, 10+ preferred. Use 100+ for list controls.

## WindowXMLDialog Gotchas

| Issue | Workaround |
|-------|-----------|
| `<include>` tags don't resolve | Inline everything — addon's Includes.xml is ignored |
| `<defaultcontrol>` on empty list fails | Default to a static control (button), set list focus in onInit after populating |
| `<control type="edit">` keyboard behind dialog | Use `<control type="button">` + `xbmc.Keyboard()` in onClick |
| `<zorder>100000` blocks keyboard | Always use `<zorder>1</zorder>` |
| Control ID 3 silently eaten | See reserved IDs table above |
