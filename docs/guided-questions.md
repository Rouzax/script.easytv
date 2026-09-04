# Guided Questions

> **Configured under** **Settings → EasyTV → Guided questions**

Before Browse Mode or Random Playlist Mode opens, EasyTV can ask you a few quick questions about what you're in the mood for and only offer shows that match. Your answers apply to that one launch only. They are never saved to settings.

---

## Why Use It?

EasyTV's usual filters (show selection, smart playlists, episode selection, premieres) are fixed until you change them in settings. Guided questions add a layer on top: a short, session-scoped mood check that narrows today's candidates without touching your saved configuration. Answer "something short and recent" one day, "anything with a rating" the next, and go back to your normal filtered list the day after that with nothing to undo.

---

## Prerequisites

- **Settings → EasyTV → Guided questions → Ask what I'm in the mood for on launch** must be On (default: Off).
- The questions run before Browse Mode or before building a Random Playlist. They do not run for a **Playlist content** of "Movies only", since there are no TV shows to narrow (see [Works With Clones](#works-with-clones-and-movies-only-playlists) below for that and clone caveats).

---

## Enabling It

1. Open **Add-ons → EasyTV → Configure**
2. Go to **EasyTV → Guided questions**
3. Turn on **Ask what I'm in the mood for on launch**
4. Optionally turn individual questions off, turn on **Remember my answers**, or turn off **Show result counts**

The next time you launch EasyTV (to Browse Mode, Random Playlist, or after choosing one from the "Ask me" launch prompt), the questions appear first.

---

## The Questions

Up to six questions can appear, in this order. Each one is a separate toggle in settings (all default On except the master switch), so you can drop any question you don't want.

| # | Question | Setting to include it |
|---|----------|------------------------|
| 1 | Genres to avoid | Ask about genres to avoid |
| 2 | Which genres? | Ask about genres |
| 3 | Episode length | Ask about episode length |
| 4 | Era | Ask about era |
| 5 | Rating | Ask about rating |
| 6 | How much to watch? | Ask about how much to watch |

Every answer narrows the candidate list for the questions that follow it, so later questions and their result counts (see [Result Counts](#result-counts)) reflect everything you've picked so far.

### 1. Genres to avoid

A multi-select list of every genre present in your candidate shows. Pick any number of genres to exclude, or pick none. Genres you avoid here are removed from the list offered by the next question.

### 2. Which genres?

A multi-select list of the remaining genres (after removing whatever you avoided in question 1). Pick any number to require at least one of; pick none to leave genre unrestricted.

If none of your candidate shows have genre metadata, both genre questions are skipped automatically.

### 3. Episode length

A single-select choice: **Short (30 min or less)**, **Medium (30-45 min)**, **Long (over 45 min)**, or **No preference**.

An answer here **replaces** your **Duration Filter** setting for this run; see [How It Interacts With Your Settings](#how-it-interacts-with-your-settings). **No preference** falls back to your existing Duration Filter setting instead.

### 4. Era

A single-select choice built from the years present in your candidate shows: **Recent (last 5 years)**, one option per decade that has shows (newest first, e.g. "2020s", "2010s"), and **No preference**.

### 5. Rating

A single-select choice: **Any rating**, **Good (7+)**, **Great (8+)**.

### 6. How much to watch?

A single-select choice about how many matching episodes a show should have available: **Anything**, **A few episodes available (3+)**, **Plenty to binge (10+)**.

What counts as an "eligible" episode depends on your **Episode selection** setting (Random Playlist → Content Options), or is fixed to unwatched episodes in Browse Mode:

| Episode selection | What "eligible episodes" counts |
|--------------------|----------------------------------|
| **Unwatched only** (and always in Browse Mode) | Remaining unwatched episodes |
| **Watched only** | Episodes already in your watch history |
| **Both** | Total episode count |

---

## How It Interacts With Your Settings

Guided questions narrow the candidates your existing settings already produce. They do not replace those settings:

- **Show filter, smart playlist, episode selection, premiere settings** all still apply first. The questions only ever narrow that set further, never widen it.
- **Duration Filter** is the one exception: if you answer the episode-length question with a length (not "No preference"), that answer replaces the Duration Filter setting for this launch. Choosing "No preference", or turning the episode-length question off entirely, falls back to your existing Duration Filter setting as usual.
- Nothing you answer is written to settings. Close EasyTV and reopen it (with **Remember my answers** off) and your saved settings are exactly as you left them.

---

## Remembered Answers

Turn on **Remember my answers** (Settings → EasyTV → Guided questions) and your choices from the last completed run are pre-selected the next time the questions appear, so repeating a mood is a few taps instead of a full run-through. They're not applied automatically; you still walk through each enabled question.

Remembered answers are stored per EasyTV instance in `wizard_answers.json` under that instance's `addon_data` folder (`special://profile/addon_data/<addon id>/wizard_answers.json`), not in settings. Turning the toggle off stops pre-selecting saved answers; it does not delete the file.

---

## Result Counts

Turn on **Show result counts** (Settings → EasyTV → Guided questions) and every answer option shows how many shows would remain if you picked it, e.g. "Comedy (12)". Counts reflect the answers you've already given to earlier questions. Turn the toggle off for a plainer list with no counts.

---

## Works With Clones and Movies-Only Playlists

Guided questions is a main-instance feature. It does not appear in a [clone's](clones.md) settings and clones cannot run it, even if the main EasyTV instance has it enabled: each clone has its own independent settings and always launches straight to Browse Mode or Random Playlist. If you want a saved mood as its own home-screen entry, build it with a clone's own [show filter](settings-reference.md#shows) or smart playlist instead.

When **Playlist content** (Random Playlist settings) is set to **Movies only**, the questions are skipped: they only narrow TV shows, and a movies-only playlist has none to narrow.

---

## When No Shows Match

If your answers leave zero shows, EasyTV shows "No shows match your answers." with two choices:

- **Adjust answers**: returns you to the first question with everything you already picked still selected, so you can loosen one or two answers rather than starting over.
- **Cancel**: closes the questions and cancels the launch.

---

## Related Pages

- **[Browse Mode](browse-mode.md):** One of the two modes guided questions can narrow
- **[Random Playlist Mode](random-playlist-mode.md):** The other mode guided questions can narrow
- **[Settings Reference](settings-reference.md):** All Guided Questions settings
- **[Clones](clones.md):** Why guided questions isn't available there, and how to build a saved mood as a clone instead
- **[Troubleshooting & FAQ](troubleshooting-and-faq.md):** "The questions found no shows"
