# EasyTV

**No scrolling. No deciding. Just watching.**

Tired of scrolling through your library wondering what to watch? EasyTV handles it. It tracks your shows and always knows your next episode. When you're ready for something new, it suggests a show you haven't started. Mix in movies if you want. Just sit down, press play, and enjoy.

Built for Kodi 21+ (Omega and newer).

---

## What is EasyTV?

Have you ever opened Kodi, looked at your library of 50+ TV shows, and thought "I don't know what to watch"? EasyTV solves this problem.

EasyTV maintains a list of the **next episode to watch** for every TV show in your library. Not just the first unwatched episode, but the first unwatched episode *after the last one you watched*. This means if you watched S01E05 last week but never marked S01E01-E04 as watched, EasyTV correctly suggests S01E06. If there are no sequential episodes available, EasyTV will suggest the earliest skipped episode so you never lose track of a show.

---

## Two Ways to Watch

EasyTV offers two fundamentally different viewing experiences. Choose your default in **Settings → When I open EasyTV**.

### Browse Mode — "Show episode list"

```
┌─────────────────────────────────────────────────────────────────────┐
│                        EasyTV Episode List                          │
├─────────────────────────────────────────────────────────────────────┤
│  Breaking Bad          S02E03 - Bit by a Dead Bee                   │
│  The Office            S04E01 - Fun Run                             │
│  Better Call Saul      S01E01 - Uno                        ← Start  │
│  Parks and Recreation  S03E12 - Eagleton                            │
│  ...                                                                │
└─────────────────────────────────────────────────────────────────────┘
                    Select a show → Play its next episode
```

**You're in control.** Browse your shows with their next episode ready to play — filtered by your preferences. Choose which shows to include (all, a manual selection, or a smart playlist), whether to show series premieres, and how to sort. Pick what you're in the mood for.

### Random Playlist — "Play random playlist"

```
┌─────────────────────────────────────────────────────────────────────┐
│  Now Playing: The Office S04E01 - Fun Run                           │
│                                                                     │
│  Up Next:                                                           │
│    1. Breaking Bad S02E03                                           │
│    2. Fargo (2014 film)                                             │
│    3. Better Call Saul S01E01                                       │
│    4. Parks and Recreation S03E12                                   │
└─────────────────────────────────────────────────────────────────────┘
                    Playback starts immediately → Channel surf
```

**Lean back and let EasyTV decide.** It builds a playlist from your shows based on your preferences — which shows to include (all, a manual selection, or a smart playlist), whether to mix in movies, whether to add series premieres, and more. Playback starts immediately. Perfect for eliminating decision fatigue while still watching what *you* want to watch.

### Can't Decide? — "Ask me"

Set the launch option to "Ask me" and EasyTV will prompt you each time:

- **"Show me"** → Opens the episode list (Browse Mode)
- **"Surprise me"** → Starts a random playlist immediately

---

## Features

### Core Features

| Feature             | Description                                                                                   |
| ------------------- | --------------------------------------------------------------------------------------------- |
| **Episode List**    | Browse all your shows with their next episode ready to play                                   |
| **Random Playlist** | One-click playlist of random next episodes — perfect for background watching                  |
| **Smart Detection** | Finds the correct next episode based on your actual watch history, including skipped episodes |
| **Auto-Update**     | Episode lists update immediately when you finish watching                                     |

### Playlist Enhancements

| Feature                | Description                                                       |
| ---------------------- | ----------------------------------------------------------------- |
| **Episode Selection**  | Include unwatched, watched, or all episodes in random playlist    |
| **Movie Integration**  | Mix unwatched (or watched) movies into your random playlist       |
| **Movie Weighting**    | Control how often movies appear vs. TV episodes                   |
| **Movie Filtering**    | Use a Kodi smart playlist to limit which movies are included      |
| **Show Filtering**     | Use a Kodi smart playlist to limit which shows are included       |
| **Random-Order Shows** | Mark shows like cartoons or sitcoms to pick any random episode    |

### Notifications

| Feature                      | Description                                             |
| ---------------------------- | ------------------------------------------------------- |
| **Next Episode Prompt**      | When an episode ends, get prompted to play the next one |
| **Previous Episode Warning** | Alert if you're about to skip an unwatched episode      |

### Advanced Features

| Feature              | Description                                                   |
| -------------------- | ------------------------------------------------------------- |
| **Smart Playlists**  | Exports three auto-updating playlists for use in other addons |
| **Episode Exporter** | Copy next episodes to a folder for offline viewing            |
| **Clone Support**    | Create multiple EasyTV instances with different settings      |

---

## Requirements

- **Kodi 21 (Omega)** or **Kodi 22 (Piers)** or later
- A TV library with watched/unwatched episodes

> ⚠️ **Not compatible** with Kodi 20 or earlier versions.

---

## Performance

EasyTV is optimized for large libraries. Performance varies significantly by hardware and database configuration.

### Measured Performance

| Device | Database | Startup | Playlist Build |
|--------|----------|---------|----------------|
| Desktop (Windows) | Local SQLite | 1-2 sec | < 1 sec |
| OSMC Vero V | Shared MySQL | 15-17 sec | ~4 sec |

### Partial Prioritization (v1.1.1 Optimization)

| Operation | Desktop | Vero V |
|-----------|---------|--------|
| Find partial TV episodes | 9ms | 84-101ms |
| Find partial movies | 12ms | 95-117ms |

### Factors Affecting Performance

- **Database location**: Shared/network databases add significant latency vs local SQLite — this is the primary factor in the difference above
- **CPU power**: ARM devices are slower than x86 desktops, but the Vero V's 4x Cortex A55 @ 2GHz is capable hardware
- **Library size**: More shows/episodes = longer queries
- **Art property queries**: Episode artwork lookups dominate startup time (optimization planned for future release)

*Tested with 168 TV shows, 5,646 episodes, and 846 movies.*

---

## Installation

### From GitHub (Recommended)
1. Download the latest release from [Releases](https://github.com/Rouzax/script.easytv/releases)
2. In Kodi: **Settings → Add-ons → Install from zip file**
3. Navigate to the downloaded zip and select it
4. EasyTV will install and start its background service automatically

### From Kodi Repository
*(Coming soon)*

### First Run
On first launch, the background service loads your TV library data. A notification appears when ready (see [Performance](#performance) for timing by device).

---

## Quick Start

### First Launch
1. Open EasyTV from your Add-ons menu (or add it to your home screen)
2. On first run, EasyTV scans your TV library — this may take a moment
3. Once ready, you'll see a list of shows with their next episodes

### Basic Usage

**Want to pick a specific show?**
→ Open EasyTV, browse the list, select your show

**Want EasyTV to decide?**
→ Open EasyTV Settings → Set "When I open EasyTV" to "Play random playlist"
→ Now launching EasyTV starts playing immediately

**Want it on your home screen?**
→ Most skins let you add add-ons to the home menu
→ Or use the Clone feature to create a dedicated "TV Time" shortcut

### Interface Styles

| Style          | Best For                               |
| -------------- | -------------------------------------- |
| **Standard**   | Detailed episode info, fast navigation |
| **Posters**    | Visual browsing with show artwork      |
| **Big Screen** | 10-foot viewing with large artwork     |

---

## Settings Reference

EasyTV's settings are organized into six categories. Open settings via **Add-ons → EasyTV → Configure** (or press `C` on the addon).

> **Note:** Some settings only appear when relevant. For example, movie settings are hidden when "Playlist content" is set to "TV episodes only".

---

### EasyTV (Main)

| Setting                | Description                                                             | Default |
| ---------------------- | ----------------------------------------------------------------------- | ------- |
| **When I open EasyTV** | What happens on launch: show episode list, play random playlist, or ask | Ask me  |

---

### Shows

These settings apply to **both** Browse Mode and Random Playlist.

#### Show Filter

| Setting                     | Description                                              | Default             |
| --------------------------- | -------------------------------------------------------- | ------------------- |
| **Use only selected shows** | Limit EasyTV to specific shows instead of entire library | Off                 |
| **Selection method**        | Choose shows manually or via smart playlist              | Pick shows manually |
| **Select shows...**         | Open dialog to pick which shows to include               | —                   |
| **Smart playlist**          | Ask each time or use a default playlist                  | Ask each time       |
| **Choose playlist file...** | Select a Kodi smart playlist (.xsp) file                 | —                   |

> When "Use only selected shows" is **Off**, EasyTV uses your entire library.  
> When **On**, additional options appear based on your chosen selection method.

#### Watch Order

| Setting                            | Description                                     | Default |
| ---------------------------------- | ----------------------------------------------- | ------- |
| **Select shows for random order...** | Select shows where episode order doesn't matter | —       |

#### Episode Options

| Setting                       | Description                                                                 | Default |
| ----------------------------- | --------------------------------------------------------------------------- | ------- |
| **Include series premieres**  | Include S01E01 from shows you haven't started                               | Off     |
| **Include season premieres**  | Include first episode of each season (S02E01, S03E01, etc.)                 | On      |

> Disable "Include season premieres" if you prefer starting new seasons from where you left off rather than from episode 1.

---

### Browse Mode

Settings for **Browse Mode** only ("Show episode list").

#### Appearance

| Setting                             | Description                                     | Default  |
| ----------------------------------- | ----------------------------------------------- | -------- |
| **View style**                      | Visual layout: Standard, Posters, or Big Screen | Standard |
| **Return to EasyTV after playback** | Come back to episode list after watching        | On       |
| **Hide random-order shows**         | Don't show random-order shows in the list       | Off      |

#### Sorting

| Setting                | Description                    | Default      |
| ---------------------- | ------------------------------ | ------------ |
| **Sort by**            | How to sort shows in the list  | Last Watched |
| **Reverse sort order** | Flip the sort direction        | Off          |

#### Performance

| Setting                   | Description                               | Default |
| ------------------------- | ----------------------------------------- | ------- |
| **Limit shows displayed** | Cap the number of shows (for performance) | Off     |
| **Maximum shows**         | How many shows when limited (1-30)        | 10      |

> "Maximum shows" is only adjustable when "Limit shows displayed" is enabled.

---

### Random Playlist

Settings for **Random Playlist Mode** only ("Play random playlist").

#### Basics

| Setting                                     | Description                                                      | Default       |
| ------------------------------------------- | ---------------------------------------------------------------- | ------------- |
| **Playlist content**                        | What to include: TV episodes only, TV and movies, or Movies only | TV and movies |
| **Playlist length**                         | Number of items in the playlist (1-50)                           | 5             |
| **Allow multiple episodes of same TV Show** | Let the same show appear multiple times in playlist              | Off           |

> "Allow multiple episodes" is hidden when content is "Movies only".

#### Content Options

*Settings appear or hide based on your "Playlist content" selection.*

| Setting                                      | Description                                                      | Default        | Visible when              |
| -------------------------------------------- | ---------------------------------------------------------------- | -------------- | ------------------------- |
| **Episode selection**                        | Which episodes to include: Unwatched only, Watched only, or Both | Unwatched only | TV episodes included      |
| **Unwatched episode chance**                 | In "Both" mode, how often to pick unwatched vs. watched          | 50%            | Episode selection = Both  |
| **Start playlist with unfinished episodes**  | Prioritize partially watched TV episodes at the start            | On             | TV episodes included      |
| **Seek to resume point for episodes**        | Auto-skip to where you left off in partial episodes              | On             | TV episodes included      |
| **Movie selection**                          | Which movies to include: Unwatched only, Watched only, or Both   | Unwatched only | Movies included           |
| **Start playlist with unfinished movies**    | Prioritize partially watched movies at the start                 | On             | Movies included           |
| **Seek to resume point for movies**          | Auto-skip to where you left off in partial movies                | On             | Movies included           |
| **Start watched movies at random point**     | Jump to a random point (5-75%) in watched movies                 | Off            | Movies included + watched |
| **Filter movies by playlist...**             | Limit which movies are included using a smart playlist           | All movies     | Movies included           |
| **Movie ratio**                              | Balance between movies and TV (0 = no movies, 1 = equal mix)     | 1.0            | TV and movies             |

> "Start watched movies at random point" is only available when "Movie selection" includes watched movies.
> 
> "Unwatched episode chance" controls the mix in "Both" mode: 80% means mostly new episodes with occasional rewatches, 20% means mostly rewatches with occasional new episodes. Unwatched episodes always play in order (next on-deck), while watched episodes are picked randomly.

#### Partial Content Prioritization

When "Start playlist with unfinished episodes/movies" is enabled, EasyTV moves **all** partially watched content to the front of the playlist — not just the most recent item.

**How it works:**

1. **All partials are prioritized** — If you have 3 shows with partial episodes and 2 partial movies, all 5 get moved to the front of the playlist
2. **Sorted by recency** — Partials are ordered by when you last watched them (most recent first)
3. **Same-show episodes stay in order** — If you have multiple partial episodes from the same show, they maintain episode order (S02E03 plays before S02E04)
4. **Respects your selection filter** — A partial only counts if it matches your Episode/Movie selection setting. For example, if "Episode selection" is "Unwatched only", a watched partial episode won't be prioritized

**Example:** You have partial episodes of Breaking Bad (watched yesterday), The Office (watched last week), and a partial movie Inception (watched 3 days ago). With both TV and movie partial settings enabled, the playlist starts:

```
1. Breaking Bad S02E05 (partial - most recent)
2. Inception (partial - 3 days ago)  
3. The Office S04E01 (partial - last week)
4. [random content continues...]
```

The "Seek to resume point" settings work independently — you can prioritize partials without auto-seeking, or vice versa.

#### Notifications

| Setting                    | Description                             | Default |
| -------------------------- | --------------------------------------- | ------- |
| **Show info when playing** | Display notification when each item starts | On      |

#### Playlist Continuation

| Setting                       | Description                                                        | Default |
| ----------------------------- | ------------------------------------------------------------------ | ------- |
| **Prompt to continue playlist** | When playlist ends, ask whether to generate another with same settings | Off     |
| **Countdown duration**        | Seconds before the prompt auto-dismisses (0 = wait indefinitely)   | 20      |

> "Countdown duration" is only adjustable when "Prompt to continue playlist" is enabled.

---

### Playback

These settings work for **all TV shows in Kodi**, not just EasyTV playback.

#### Next Episode Prompt

| Setting                                 | Description                                        | Default    |
| --------------------------------------- | -------------------------------------------------- | ---------- |
| **Ask to watch next episode**           | Show prompt after an episode ends                  | On         |
| **Prompt timeout (seconds)**            | How long the prompt stays on screen (60 = forever) | 20         |
| **If prompt times out**                 | Default action: Don't play or Play next episode    | Don't play |
| **Also prompt during random playlists** | Show prompt even during EasyTV playlists           | Off        |

> The timeout, default action, and playlist prompt settings are only adjustable when "Ask to watch next episode" is enabled.

#### Warnings

| Setting                                   | Description                            | Default |
| ----------------------------------------- | -------------------------------------- | ------- |
| **Warn about earlier unwatched episodes** | Alert if skipping an unwatched episode | Off     |

---

### Advanced

Technical settings and utilities.

#### Background Service

| Setting                                   | Description                                   | Default |
| ----------------------------------------- | --------------------------------------------- | ------- |
| **Show notification when ready**          | Notify when library scan completes on startup | On      |
| **Auto-create 'Next Episodes' playlists** | Maintain smart playlists for other addons     | Off     |

#### Debugging

| Setting                  | Description                                       | Default |
| ------------------------ | ------------------------------------------------- | ------- |
| **Enable debug logging** | Write detailed diagnostics to a separate log file | Off     |

#### Tools

| Setting                          | Description                            |
| -------------------------------- | -------------------------------------- |
| **Create EasyTV copy...**        | Create a clone with separate settings  |
| **Export episodes to folder...** | Copy next episodes for offline viewing |

---

## Smart Playlists

When **Auto-create 'Next Episodes' playlists** is enabled (in **Settings → Advanced → Background Service**), EasyTV creates three `.xsp` files in your Kodi profile's playlist folder:

| Playlist                       | Contents                           | Use Case                       |
| ------------------------------ | ---------------------------------- | ------------------------------ |
| **EasyTV - All Shows**         | Every show with an on-deck episode | "Surprise me with anything"    |
| **EasyTV - Continue Watching** | Shows mid-season (episode 2+)      | "Continue something I started" |
| **EasyTV - Start Fresh**       | Shows at season start (episode 1)  | "Start something new"          |

### How Categorization Works

Shows are categorized by their **next episode number**:

```
Episode 1 (any season) → "Start Fresh"
Episode 2, 3, 4, ...   → "Continue Watching"
```

As you watch, shows automatically move between playlists:

```
You're at S01E01 → Show is in "Start Fresh"
        │
        ▼ (you watch S01E01)
        │
You're at S01E02 → Show moves to "Continue Watching"
        │
        ▼ (you watch all of season 1)
        │
You're at S02E01 → Show moves back to "Start Fresh"
```

### Using with Other Addons

These playlists work with:
- **PseudoTV Live** — Create channels from EasyTV playlists
- **Skin widgets** — Show "Continue Watching" on your home screen
- **Other smart playlists** — Use as criteria in your own playlists

**Playlist location:** `special://profile/playlists/video/`

---

## Random-Order Shows

Some shows don't need to be watched in order (sitcoms, cartoons, sketch comedy). For these shows:

1. Go to **Settings → Shows → Watch Order**
2. Click **Choose shows...** to select shows that can be watched in any order
3. EasyTV will pick a random episode instead of the "next" episode

When you add a show to this list, EasyTV immediately shuffles to a random episode.

> **Note:** You can hide random-order shows from the episode list in **Settings → Browse Mode → Appearance → Hide random-order shows**. They'll still appear in random playlists.

### How Episode Selection Interacts with Random-Order

The **Episode selection** setting (Unwatched/Watched/Both) works differently for sequential vs. random-order shows:

| Episode Selection | Sequential Shows | Random-Order Shows |
|-------------------|------------------|-------------------|
| **Unwatched** | Next episode in order (S02E05 → S02E06 → S02E07) | Random unwatched episode |
| **Watched** | Random rewatch | Random rewatch |
| **Both** | Mix of next-in-order + random rewatches | Mix of random unwatched + random rewatches |

Key points:
- **Unwatched mode** always picks from unwatched episodes only — random-order just means *which* unwatched episode is picked randomly instead of sequentially
- **Watched mode** is the same for both — random rewatches
- **Both mode** uses the "Unwatched episode chance" slider (configurable for both sequential and random-order shows) to balance the mix — for random-order shows, both sides of that mix are random (random unwatched vs. random watched)

---

## Clone Feature

Create multiple EasyTV instances with different settings. For example:
- **EasyTV Kids** — Filtered to only children's shows
- **EasyTV Comedies** — Only comedy shows, movies included

### Creating a Clone
1. Go to EasyTV **Settings → Advanced → Tools**
2. Click **Create EasyTV copy...**
3. Enter a name for the clone
4. The clone appears as a separate addon in Program Add-ons
5. Configure the clone's settings independently

### Clone Updates
When you update EasyTV, clones are updated automatically — when you launch an outdated clone, EasyTV detects the version mismatch and prompts you to update it.

---

## Troubleshooting

### "EasyTV Service is not running"
The background service must be running for EasyTV to work.

1. Go to **Settings → Add-ons → My add-ons → Services**
2. Find **EasyTV** and ensure it's enabled
3. Restart Kodi if needed

### Empty Episode List
- Wait for the initial library scan (notification shows when complete)
- Ensure you have TV shows with unwatched episodes
- If using "Use only selected shows," make sure you've selected some shows
- Try **Context menu → Refresh List**

### Episodes not marking as watched
EasyTV relies on Kodi's watch status. Check:
- Settings → Player → Videos → "Minimum percentage watched" (default 90%)
- Your Kodi library is updating properly

### Poor Performance
On low-power devices (Raspberry Pi, older Fire TV):
- Enable **Limit shows displayed** in **Settings → Browse Mode → Performance**
- Set maximum to 10-15 shows
- Use **Standard** view style instead of Posters

### Debug Logging

EasyTV writes detailed debug logs to a **separate file** (not Kodi's main log):

1. Enable **Enable debug logging** in **Settings → Advanced → Debugging**
2. Reproduce the issue
3. Find the log file at:
   - **Windows:** `%APPDATA%\Kodi\userdata\addon_data\script.easytv\logs\easytv.log`
   - **Linux:** `~/.kodi/userdata/addon_data/script.easytv/logs/easytv.log`
   - **macOS:** `~/Library/Application Support/Kodi/userdata/addon_data/script.easytv/logs/easytv.log`
   - **LibreELEC/OSMC:** `/storage/.kodi/userdata/addon_data/script.easytv/logs/easytv.log`

Important events (INFO/WARNING/ERROR) also appear in Kodi's main log — search for `[EasyTV.service]` or `[EasyTV.default]`.

See [LOGGING.md](LOGGING.md) for detailed logging documentation.

---

## Translations

EasyTV is prepared for the [Kodi Weblate](https://kodi.weblate.cloud/) translation system. Once submitted to the official Kodi addon repository, translations can be contributed through Weblate.

The source language is British English (`resource.language.en_gb`).

---

## Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

**Quick links:**
- [Report a bug](https://github.com/Rouzax/script.easytv/issues/new?template=bug_report.md)
- [Suggest a feature](https://github.com/Rouzax/script.easytv/issues/new)

---

## Credits & License

### Original Author
**KODeKarnage** — Created LazyTV in 2013
- Original repository: https://github.com/KODeKarnage/script.lazytv
- Kodi forum thread: https://forum.kodi.tv/showthread.php?tid=170975

### Current Maintainer  
**Rouzax** — Modernized for Kodi 21+ (2024-2026)
- Repository: https://github.com/Rouzax/script.easytv
- Kodi forum thread: https://forum.kodi.tv/showthread.php?tid=383902

### License
This project is licensed under the **GNU General Public License v3.0** (GPL-3.0-or-later).

You are free to use, modify, and distribute this software under the terms of the GPL. See [LICENSE.txt](LICENSE.txt) for the full license text.

---

*EasyTV — Because your library should work for you, not the other way around.*