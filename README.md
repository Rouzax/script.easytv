# EasyTV

**No scrolling. No deciding. Just watching.**

EasyTV transforms your Kodi library into a personal TV channel. It tracks the next episode for every TV show and lets you dive right in, or creates randomized playlists for lean-back viewing.

![EasyTV Split View](docs/assets/screenshots/view-split-golden-hour.png)

Built for Kodi 21+ (Omega and newer).

---

## What is EasyTV?

EasyTV maintains a list of the **next episode to watch** for every TV show in your library. Not just the first unwatched episode, but the first unwatched episode *after the last one you watched*.

### Two Ways to Watch

| Mode | Experience |
|------|------------|
| **Browse Mode** | See all your shows with their next episode. Pick what you're in the mood for. |
| **Random Playlist** | One click starts a shuffled playlist. Sit back and let EasyTV decide. |

---

## Key Features

- **Smart Episode Tracking**: Always knows your next episode, even with gaps in watch history
- **Multi-Instance Sync**: Share watch progress across multiple Kodi devices
- **Mix in Movies**: Add movies to your random playlists
- **Smart Playlist Filtering**: Use Kodi smart playlists to filter content
- **Duration Filtering**: Only shows with episodes under 30 minutes? Done.
- **Random-Order Shows**: Shuffle-friendly content like sitcoms and cartoons
- **Positioned Specials**: Include TVDB-positioned specials in the watch order
- **Partial Prioritization**: Unfinished content plays first
- **Clone Support**: Multiple EasyTV instances with different configurations

---

## Requirements

- **Kodi 21 (Omega)** or **Kodi 22 (Piers)** or later
- A TV library with watched/unwatched episodes

> ⚠️ **Not compatible** with Kodi 20 or earlier versions.

---

## Multi-Instance Sync (Optional)

If you run Kodi on multiple devices (living room, bedroom, etc.) with a **shared MySQL/MariaDB video database**, EasyTV can sync watch progress between them. When you watch Episode 5 on one device, all other devices know to queue Episode 6.

**Requirements:**
- Kodi configured with a shared MySQL/MariaDB video database
- `script.module.pymysql` Kodi addon (Kodi installs it automatically as an EasyTV dependency)

**Quick Setup:**
1. Enable **"Enable multi-instance sync"** in **Settings → Advanced → Multi-Instance Sync** on every device
2. That's it: EasyTV auto-detects your database from `advancedsettings.xml`

> **Note:** Some settings affect episode ordering and must match across all synced devices: **Random-order shows** and **Include positioned specials**. Mismatched settings will cause each device to calculate different "next episodes."

For detailed setup, see the [Multi-Instance Sync](https://rouzax.github.io/script.easytv/docs/multi-instance-sync/) documentation.

---

## Installation

Three ways to install. Pick whichever fits how you want updates delivered:

- **[Rouzax Repository](https://github.com/Rouzax/repository.rouzax/releases)** *(recommended)*: install the repository zip once; Kodi auto-updates EasyTV (and the other Rouzax addons) on every stable release.
- **Official Kodi Add-on Repository**: pre-enabled in every Kodi install. **Settings → Add-ons → Install from repository → Kodi Add-on repository → Program add-ons → EasyTV**. Versions can lag while a release goes through Kodi review.
- **[GitHub releases](https://github.com/Rouzax/script.easytv/releases)** (latest, manual): download the `script.easytv-vX.Y.Z.zip`, then **Settings → Add-ons → Install from zip file**. Use this for pre-releases (alpha/beta) or to grab a release before it reaches the repositories.

After install, wait for the "Database analysis complete" notification, then launch EasyTV from **Add-ons → Program add-ons**.

See the [Installation page in the docs](https://rouzax.github.io/script.easytv/docs/installation/) for full step-by-step instructions, requirements, and first-run tips.

---

## 📖 Documentation

**Full documentation is available on the [docs site](https://rouzax.github.io/script.easytv/docs/):**

| Page | Description |
|------|-------------|
| [Installation](https://rouzax.github.io/script.easytv/docs/installation/) | Setup and first run |
| [Browse Mode](https://rouzax.github.io/script.easytv/docs/browse-mode/) | Episode list guide |
| [Random Playlist Mode](https://rouzax.github.io/script.easytv/docs/random-playlist-mode/) | Shuffled playlists |
| [Settings Reference](https://rouzax.github.io/script.easytv/docs/settings-reference/) | All settings explained |
| [Smart Playlist Integration](https://rouzax.github.io/script.easytv/docs/smart-playlist-integration/) | Advanced filtering |
| [Smart Playlist Examples](https://rouzax.github.io/script.easytv/docs/smart-playlist-examples/) | Ready-to-use playlist files |
| [Random-Order Shows](https://rouzax.github.io/script.easytv/docs/random-order-shows/) | Shuffle-friendly content |
| [Clones](https://rouzax.github.io/script.easytv/docs/clones/) | Multiple EasyTV instances with independent settings |
| [Episode Export](https://rouzax.github.io/script.easytv/docs/episode-export/) | Copy next episodes for offline viewing |
| [Auto-Generated Playlists](https://rouzax.github.io/script.easytv/docs/auto-generated-playlists/) | Smart playlists for skin widgets and channel surfing |
| [Multi-Instance Sync](https://rouzax.github.io/script.easytv/docs/multi-instance-sync/) | Share progress across devices |
| [Troubleshooting & FAQ](https://rouzax.github.io/script.easytv/docs/troubleshooting-and-faq/) | Common issues |

---

## Quick Links

- **[Report a Bug](https://github.com/Rouzax/script.easytv/issues/new)**
- **[Kodi Forum Thread](https://forum.kodi.tv/showthread.php?tid=383902)**
- **[Changelog](changelog.txt)**

---

## Credits & License

EasyTV began in 2024 as a fork of [LazyTV](https://github.com/KODeKarnage/script.lazytv) by KODeKarnage (2013). It has since been completely rewritten.

This project is licensed under the **GNU General Public License v3.0** (GPL-3.0-only).

See [LICENSE.txt](LICENSE.txt) for the full license text.

---

*EasyTV: Because your library should work for you, not the other way around.*
