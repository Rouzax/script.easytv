# EasyMovie UI Parity Design

**Date:** 2026-03-23
**Status:** Approved
**Scope:** Port EasyMovie's dialog/browse refinements to EasyTV

## Context

EasyMovie (sibling addon for movies) has received significant UI refinements:
- Descender padding rules for stacked labels
- Full-screen heading area standard
- Standardized heading layouts across all views
- Item count display in browse headers
- Rich poster dialogs (set warning, continuation)
- InfoTagVideo-populated ListItems
- PosterGrid browse mode (5th view)

EasyTV needs to incorporate these refinements while respecting the metadata differences between movies and TV show episodes.

## Key Constraint: TV vs Movie Metadata Density

TV show browse views display more metadata than movie views:
- Episode code + episode title (movies have just title)
- On Deck / Watched / Skipped counts (movies have watched boolean)
- Last watched date + progress percentage (movies don't track this)
- Genre + duration per episode (similar to movies)

When adjusting spacing and layout, TV views need more vertical room for metadata rows. Positions cannot be copied directly from EasyMovie.

## Phase 1: Guidelines & Includes.xml

No functional changes. Updates documentation and fixes one texture inconsistency.

### skin-guidelines.md additions

**Descender Padding Rule:**
- Minimum 4px visual gap between stacked labels to prevent descender overlap (g, y, p)
- Formula: `eff_bottom = top + (height + font_px) / 2`, `eff_top = top + (height - font_px) / 2`, `gap = next_eff_top - prev_eff_bottom (must be >= 4px)`
- Font reference sizes: font10 ~21px, font12 ~24px, font13 ~30px, font14_title ~32px

**Full-Screen Heading Area Standard** (for Posters and BigScreen views):
- Heading top: 15, height: 40
- Count top: 20, font10, right-aligned
- Accent line top: 60, height: 2
- Content top: 72
- Side padding: 40 (BigScreen uses 80 for cinematic feel)

**Item count convention:**
- `$INFO[Container(655).CurrentItem] / $INFO[Container(655).NumItems]`

### Includes.xml fix

Change EasyTV_Separator texture from `common/white.png` to `common/line_fade.png` to match the guideline and EasyMovie.

## Phase 2: Browse View Heading Standardization

### Dialog-style views (CardList, SplitView)

- Move accent line from current `top=46` to `top=66`
- Move content/list start to `top=82`
- Add item count label (right-aligned, font10, FF888888)
- Full-width accent line spanning both panels where applicable
- Adjust list heights to compensate for later content start

### Full-screen views (Posters, BigScreen)

- Apply full-screen heading standard: heading top=15, accent line top=60, content top=72
- Add item count label
- Side padding: 40 for Posters, 80 for BigScreen

### Descender padding audit

- Verify every stacked label pair across all 4 browse view XMLs
- Fix any gaps < 4px by adjusting `top` values
- Respect TV metadata density — don't compress rows to match EasyMovie positions

## Phase 3: Dialog Refinements

### New missed episode warning dialog

Currently: `show_confirm()` → basic `ConfirmDialog` (720x240, text-only, no poster)

New: `script-easytv-missedwarning.xml` (800x480) modeled on EasyMovie's `script-easymovie-setwarning.xml`:
- Control IDs: 1 (heading), 2 (message), 4 (subtitle), 10 (yes), 11 (no), 20 (poster)
- Show poster (160x240) on left
- Rich multiline message to the right (font13)
- Centered subtitle/question (font12)
- Two buttons at bottom
- Reuses `CountdownDialog` class with `duration=0` (no timer) — no new Python class needed

Python change: update `_check_previous_episode()` in `playback_monitor.py` to use `CountdownDialog` with new XML instead of `show_confirm()`, passing the show poster.

### Next episode dialog fixes

- Change message label font from `font14_title` to `font13` (typography rule: font14_title is for headings only)
- Descender padding verification on all label pairs

### Countdown dialog audit

- Descender padding verification (text-only dialog, no poster — stays as-is)

### Full dialog descender audit

Covers all dialog XMLs: confirm, countdown, nextepisode, missedwarning, select, selector, contextwindow.

## Phase 4: InfoTagVideo Expansion

### browse_window.py changes

Expand `_create_list_item()` to set additional InfoTagVideo fields from existing window property data:
- `info_tag.setYear()` — from `EasyTV.{show_id}.Year`
- `info_tag.setGenres()` — from `EasyTV.{show_id}.Genre` (split comma-separated string to list)
- `info_tag.setDuration()` — from `EasyTV.{show_id}.Duration`

No service-side changes needed — all data already available in window properties.

Not adding: Rating and MPAA (not stored by service, not relevant for TV show episode browsing).

### Skin XML updates

Update detail panels in SplitView, BigScreen, and Posters to use `$INFO[ListItem.Year]`, `$INFO[ListItem.Genre]`, `$INFO[ListItem.Duration]` where appropriate, alongside existing custom properties.

## Phase 5: PosterGrid View

### New XML: `script-easytv-postergrid.xml`

Full-screen horizontal `fixedlist` with `focusposition=1`, modeled on EasyMovie's `script-easymovie-postergrid.xml`.

Layout:
- Header: addon name (left) + item count (right) + accent line (full-screen heading standard)
- Filmstrip: horizontal fixedlist, unfocused ~182x273, focused ~420x630 with accent border and zoom animation
- Poster badges: watched icon (`IconWatched.png`) with `scrim_topleft.png` overlay
- Info panel below filmstrip:
  - Left: Show title (font13, Accent), episode code + title (font10, white), genre · ~duration/ep (font10, FFAAAAAA), on deck/watched/skipped counts (font10, FFAAAAAA with Accent values)
  - Right: Plot (font12, FFAAAAAA, autoscroll textbox)

### Python changes

- Add `VIEW_POSTER_GRID` constant to `constants.py`
- Add mapping in `get_skin_xml_file()` as skin=4
- Add option to view style settings picker

### New assets

- `resources/skins/Default/media/common/scrim_topleft.png` — gradient overlay for watched badge on posters (copy from EasyMovie)

## Phase Dependencies

```
Phase 1 (Guidelines) ──→ Phase 2 (Headings)
                     └──→ Phase 5 (PosterGrid)
Phase 2 (Headings)  ──→ Phase 4 (InfoTagVideo)
Phase 3 (Dialogs)       [independent]
Phase 4 (InfoTagVideo) ──→ Phase 5 (PosterGrid)
```

Phase 3 can run in parallel with Phase 2. Phase 5 is last because it depends on both the guidelines (Phase 1) and InfoTagVideo expansion (Phase 4) being in place.
