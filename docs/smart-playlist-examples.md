# Smart Playlist Examples

Ready-to-use smart playlist files for common filtering scenarios. Copy the XML code or download the `.xsp` files directly.

---

## How to Use These Examples

### Option 1: Copy the XML

1. Copy the XML code from the example
2. Open a text editor (Notepad, VS Code, etc.)
3. Paste the code
4. Save as `filename.xsp` (not `.txt`)
5. Move the file to your Kodi playlists folder:
   - **Windows:** `%APPDATA%\Kodi\userdata\playlists\video\`
   - **Linux:** `~/.kodi/userdata/playlists/video/`
   - **macOS:** `~/Library/Application Support/Kodi/userdata/playlists/video/`
   - **LibreELEC/OSMC:** `/storage/.kodi/userdata/playlists/video/`

### Option 2: Download the File

Download links are provided for each example. Save directly to your playlists folder.

### After Adding Playlists

1. Restart Kodi (or go to Videos → Playlists to verify)
2. In EasyTV settings, select the playlist for filtering

---

## TV Show Playlists

### TV Shows - Comedy

Filter to comedy content.

```xml
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<smartplaylist type="tvshows">
    <n>TV Shows - Comedy</n>
    <match>all</match>
    <rule field="genre" operator="is">
        <value>Comedy</value>
    </rule>
</smartplaylist>
```

📥 **Download:** [TV Shows - Comedy.xsp](https://raw.githubusercontent.com/Rouzax/script.easytv/main/docs/smart-playlists/TV%20Shows%20-%20Comedy.xsp)

---

### TV Shows - Drama and Thriller

Serious content for focused viewing.

```xml
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<smartplaylist type="tvshows">
    <n>TV Shows - Drama and Thriller</n>
    <match>one</match>
    <rule field="genre" operator="is">
        <value>Drama</value>
    </rule>
    <rule field="genre" operator="is">
        <value>Thriller</value>
    </rule>
    <rule field="genre" operator="is">
        <value>Crime</value>
    </rule>
</smartplaylist>
```

📥 **Download:** [TV Shows - Drama and Thriller.xsp](https://raw.githubusercontent.com/Rouzax/script.easytv/main/docs/smart-playlists/TV%20Shows%20-%20Drama%20and%20Thriller.xsp)

---

### TV Shows - HBO and Netflix

Content from specific streaming networks.

```xml
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<smartplaylist type="tvshows">
    <n>TV Shows - HBO and Netflix</n>
    <match>one</match>
    <rule field="studio" operator="contains">
        <value>HBO</value>
    </rule>
    <rule field="studio" operator="contains">
        <value>Netflix</value>
    </rule>
</smartplaylist>
```

📥 **Download:** [TV Shows - HBO and Netflix.xsp](https://raw.githubusercontent.com/Rouzax/script.easytv/main/docs/smart-playlists/TV%20Shows%20-%20HBO%20and%20Netflix.xsp)

---

### TV Shows - Binge-Ready

Shows with at least 10 episodes that you haven't fully watched. Perfect for a marathon.

```xml
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<smartplaylist type="tvshows">
    <n>TV Shows - Binge-Ready</n>
    <match>all</match>
    <rule field="numberofepisodes" operator="greaterthan">
        <value>10</value>
    </rule>
    <rule field="playcount" operator="is">
        <value>0</value>
    </rule>
</smartplaylist>
```

📥 **Download:** [TV Shows - Binge-Ready.xsp](https://raw.githubusercontent.com/Rouzax/script.easytv/main/docs/smart-playlists/TV%20Shows%20-%20Binge-Ready.xsp)

---

### TV Shows - Animation

All animated content. Works great with EasyTV's random-order shows feature.

```xml
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<smartplaylist type="tvshows">
    <n>TV Shows - Animation</n>
    <match>all</match>
    <rule field="genre" operator="is">
        <value>Animation</value>
    </rule>
</smartplaylist>
```

📥 **Download:** [TV Shows - Animation.xsp](https://raw.githubusercontent.com/Rouzax/script.easytv/main/docs/smart-playlists/TV%20Shows%20-%20Animation.xsp)

---

### TV Shows - Documentary

Educational and documentary content.

```xml
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<smartplaylist type="tvshows">
    <n>TV Shows - Documentary</n>
    <match>all</match>
    <rule field="genre" operator="is">
        <value>Documentary</value>
    </rule>
</smartplaylist>
```

📥 **Download:** [TV Shows - Documentary.xsp](https://raw.githubusercontent.com/Rouzax/script.easytv/main/docs/smart-playlists/TV%20Shows%20-%20Documentary.xsp)

---

## Movie Playlists

### Movies - Kids

Family content based on folder location. This playlist serves as a building block that other playlists can exclude.

```xml
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<smartplaylist type="movies">
    <n>Movies - Kids</n>
    <match>all</match>
    <rule field="path" operator="contains">
        <value>/Kids/</value>
    </rule>
</smartplaylist>
```

📥 **Download:** [Movies - Kids.xsp](https://raw.githubusercontent.com/Rouzax/script.easytv/main/docs/smart-playlists/Movies%20-%20Kids.xsp)

> **Path filtering:** This uses the `path` field to include movies stored in a `/Kids/` folder. Adjust the value to match your folder structure. Path-based filtering is reliable when you've organized your library by audience or content type.

---

### Movies - 80s and 90s

Nostalgic content from two classic decades, excluding kids content by referencing the Kids playlist.

```xml
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<smartplaylist type="movies">
    <n>Movies - 80s and 90s</n>
    <match>all</match>
    <rule field="year" operator="greaterthan">
        <value>1979</value>
    </rule>
    <rule field="year" operator="lessthan">
        <value>2000</value>
    </rule>
    <rule field="playlist" operator="isnot">
        <value>Movies - Kids</value>
    </rule>
</smartplaylist>
```

📥 **Download:** [Movies - 80s and 90s.xsp](https://raw.githubusercontent.com/Rouzax/script.easytv/main/docs/smart-playlists/Movies%20-%2080s%20and%2090s.xsp)

> **Playlist exclusion:** This example uses `playlist` with `isnot` to exclude all movies that appear in the "Movies - Kids" playlist. This is powerful because:
> - You define "kids content" once in the Kids playlist
> - Any playlist can then exclude it with a single rule
> - Changes to the Kids playlist automatically apply everywhere

---

### Movies - Highly Rated

Movies with rating of 7 or higher.

```xml
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<smartplaylist type="movies">
    <n>Movies - Highly Rated</n>
    <match>all</match>
    <rule field="rating" operator="greaterthan">
        <value>6.9</value>
    </rule>
</smartplaylist>
```

📥 **Download:** [Movies - Highly Rated.xsp](https://raw.githubusercontent.com/Rouzax/script.easytv/main/docs/smart-playlists/Movies%20-%20Highly%20Rated.xsp)

---

### Movies - 4K UHD

Movies in 4K resolution. Show off your setup.

```xml
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<smartplaylist type="movies">
    <n>Movies - 4K UHD</n>
    <match>all</match>
    <rule field="videoresolution" operator="greaterthan">
        <value>1080</value>
    </rule>
</smartplaylist>
```

📥 **Download:** [Movies - 4K UHD.xsp](https://raw.githubusercontent.com/Rouzax/script.easytv/main/docs/smart-playlists/Movies%20-%204K%20UHD.xsp)

---

### Movies - Quality Unwatched

Highly rated movies you haven't seen. The best of your backlog.

```xml
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<smartplaylist type="movies">
    <n>Movies - Quality Unwatched</n>
    <match>all</match>
    <rule field="playcount" operator="is">
        <value>0</value>
    </rule>
    <rule field="rating" operator="greaterthan">
        <value>7</value>
    </rule>
</smartplaylist>
```

📥 **Download:** [Movies - Quality Unwatched.xsp](https://raw.githubusercontent.com/Rouzax/script.easytv/main/docs/smart-playlists/Movies%20-%20Quality%20Unwatched.xsp)

---

### Movies - Date Night

Romantic movies that are actually good.

```xml
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<smartplaylist type="movies">
    <n>Movies - Date Night</n>
    <match>all</match>
    <rule field="genre" operator="is">
        <value>Romance</value>
    </rule>
    <rule field="rating" operator="greaterthan">
        <value>6</value>
    </rule>
</smartplaylist>
```

📥 **Download:** [Movies - Date Night.xsp](https://raw.githubusercontent.com/Rouzax/script.easytv/main/docs/smart-playlists/Movies%20-%20Date%20Night.xsp)

---

### Movies - Christmas

Seasonal content using custom tags.

```xml
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<smartplaylist type="movies">
    <n>Movies - Christmas</n>
    <match>all</match>
    <rule field="tag" operator="is">
        <value>christmas</value>
    </rule>
</smartplaylist>
```

📥 **Download:** [Movies - Christmas.xsp](https://raw.githubusercontent.com/Rouzax/script.easytv/main/docs/smart-playlists/Movies%20-%20Christmas.xsp)

> **Using tags:** This playlist requires you to add a "christmas" tag to your movies in Kodi. Edit a movie's info and add the tag manually. Tags are great for creating custom collections that don't fit standard metadata like genre or year (think "Halloween", "Summer", "Comfort Movies", etc.).
>
> **Note:** Your library may already have scraper-added tags like "sequel", "based on novel or book", or "female protagonist". Check your library to see what's available. You might be able to create interesting playlists without any manual tagging.

---

### Movies - Short

Movies under 100 minutes for when time is limited.

```xml
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<smartplaylist type="movies">
    <n>Movies - Short</n>
    <match>all</match>
    <rule field="time" operator="lessthan">
        <value>100</value>
    </rule>
</smartplaylist>
```

📥 **Download:** [Movies - Short.xsp](https://raw.githubusercontent.com/Rouzax/script.easytv/main/docs/smart-playlists/Movies%20-%20Short.xsp)

---

## Understanding Smart Playlists

### Match Rules

The `<match>` element controls how multiple rules combine:

| Match | Logic | Use When |
|-------|-------|----------|
| `all` | AND | Content must match ALL rules |
| `one` | OR | Content must match ANY rule |

**Important:** When excluding content (using `isnot`, `doesnotcontain`), always use `match all`. Exclusions with OR logic can cause unexpected results.

### Common Operators

| Operator | Use For |
|----------|---------|
| `is` | Exact match |
| `isnot` | Exclude exact match |
| `contains` | Partial text match |
| `doesnotcontain` | Exclude partial match |
| `greaterthan` | Numbers above value |
| `lessthan` | Numbers below value |
| `inthelast` | Date within period (e.g., "30 days") |

### Playlist Referencing

Playlists can reference other playlists using the `playlist` field. This is powerful for creating reusable building blocks:

```xml
<!-- Include content from another playlist -->
<rule field="playlist" operator="is">
    <value>Movies - Kids</value>
</rule>

<!-- Exclude content from another playlist -->
<rule field="playlist" operator="isnot">
    <value>Movies - Kids</value>
</rule>
```

**Use cases:**
- Define "Kids content" once, exclude it from multiple adult playlists
- Create a "Favorites" playlist, then make "Unwatched Favorites"
- Build complex filters by combining simpler playlists

**Important:** The referenced playlist must exist and have the exact same name (case-sensitive).

---

## Common Genres

Genres depend on your scraper and library. These are typically available:

**Widely used:** Action, Adventure, Animation, Comedy, Crime, Documentary, Drama, Family, Fantasy, History, Horror, Music, Mystery, Romance, Science Fiction, Thriller, War, Western

**Less common:** Kids, News, Reality, Talk, TV Movie

**Combined genres:** Some scrapers provide "Action & Adventure" or "Sci-Fi & Fantasy". These are rare and library-dependent.

> **Tip:** Check your own library's genres before creating playlists. In Kodi, go to Videos → Movies → Genres to see what's actually in your database.

---

## Available Fields Reference

### TV Show Fields

`title`, `originaltitle`, `plot`, `tvshowstatus`, `votes`, `rating`, `userrating`, `year`, `genre`, `director`, `actor`, `numberofepisodes`, `numberofwatchedepisodes`, `playcount`, `path`, `studio`, `mpaa`, `dateadded`, `lastplayed`, `inprogress`, `tag`, `playlist`

### Movie Fields

`title`, `originaltitle`, `plot`, `plotoutline`, `tagline`, `votes`, `rating`, `userrating`, `time`, `writer`, `playcount`, `lastplayed`, `inprogress`, `genre`, `country`, `year`, `director`, `actor`, `mpaa`, `top250`, `studio`, `trailer`, `filename`, `path`, `set`, `tag`, `dateadded`, `videoresolution`, `audiochannels`, `audiocount`, `subtitlecount`, `videocodec`, `audiocodec`, `audiolanguage`, `subtitlelanguage`, `videoaspectratio`, `hdrtype`, `playlist`

> **Reference:** [Kodi Wiki - Smart Playlist Rules](https://kodi.wiki/view/Smart_playlists/Rules_and_groupings)

---

## Tips for Creating Your Own

1. **Check your library first:** Go to Videos → Movies → Genres (or Tags) to see what values actually exist in your database. Genres and tags are library-dependent.

2. **Start in the GUI:** Create playlists using Kodi's built-in editor first, then examine the `.xsp` file to learn the correct field names and syntax.

3. **Use path filtering:** When metadata is inconsistent, filtering by folder path (`/Kids/`, `/4K/`, `/Documentaries/`) is reliable.

4. **Leverage existing tags:** Your scraper may have already added useful tags like "sequel", "based on novel or book", etc. Check what's available before manually tagging.

5. **Build reusable playlists:** Create base playlists (like "Movies - Kids") that other playlists can reference or exclude.

6. **Combine with EasyTV:** Use playlists for broad filtering, then use EasyTV's duration and episode settings for fine-tuning.

---

## Related Pages

- **[Smart Playlist Integration](smart-playlist-integration.md):** How filtering works with EasyTV
- **[Settings Reference](settings-reference.md):** All EasyTV settings
- **[Random-Order Shows](random-order-shows.md):** Shuffle-friendly content setup
