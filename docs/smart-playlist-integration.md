# Smart Playlist Integration

Smart playlists are one of Kodi's most powerful features, and EasyTV fully integrates with them. This unlocks endless filtering possibilities: watch only comedies, only shows from the 2000s, only highly-rated movies, or any combination you can imagine.

---

## What Are Smart Playlists?

Smart playlists are dynamic filters that automatically include content matching your criteria. Unlike regular playlists where you manually add items, smart playlists update themselves as your library changes.

**Examples:**
- "All Comedy Shows" - Automatically includes any show tagged as Comedy
- "Movies from the 90s" - Includes movies released 1990-1999
- "Recently Added" - Shows content added in the last 30 days

---

## How EasyTV Uses Smart Playlists

EasyTV can filter content using smart playlists in three places:

| Location | Filter Type | Settings Path |
|----------|-------------|---------------|
| **TV Show Filter** | Which shows appear in EasyTV | Settings → Shows → Show Filter |
| **Movie Filter** | Which movies appear in random playlists | Settings → Random Playlist → Content Options |
| **Auto-Created Playlists** | EasyTV exports for other addons | Settings → Advanced → Background Service |

---

## Filtering TV Shows

### Setting Up Show Filtering

1. Go to **Settings → Shows → Show Filter**
2. Enable **Use only selected shows**
3. Set **Selection method** to **Use a smart playlist**
4. Choose **Ask each time** or **Use default**:
   - **Ask each time:** EasyTV prompts you to pick a playlist when you launch
   - **Use default:** Uses the same playlist every time
5. If using default, click **Choose playlist file...** to select your `.xsp` file

### What Gets Filtered

When a TV show smart playlist is active:
- **Browse Mode** shows only shows matching the playlist
- **Random Playlist** only picks episodes from matching shows
- All other settings (duration filter, premieres, etc.) still apply on top

### Creating a TV Show Playlist

In Kodi:
1. Go to **Videos → TV Shows**
2. Open the sidebar menu (usually left arrow)
3. Select **New smart playlist...**
4. Set **Playlist type** to **TV Shows**
5. Add your rules (see [Creating Rules](#creating-rules) below)
6. Save the playlist

---

## Filtering Movies

### Setting Up Movie Filtering

1. Go to **Settings → Random Playlist → Content Options**
2. Make sure **Playlist content** includes movies
3. Click **Filter movies by playlist...**
4. Select a movie smart playlist

### What Gets Filtered

When a movie smart playlist is active:
- Only movies matching the playlist can appear in random playlists
- Other movie settings (selection, partials, etc.) still apply

### Creating a Movie Playlist

In Kodi:
1. Go to **Videos → Movies**
2. Open the sidebar menu
3. Select **New smart playlist...**
4. Set **Playlist type** to **Movies**
5. Add your rules
6. Save the playlist

---

## Creating Rules

Smart playlists use rules to filter content. Each rule has three parts:

| Part | Description | Example |
|------|-------------|---------|
| **Field** | What to check | Genre, Year, Rating, Studio |
| **Operator** | How to compare | is, contains, greater than |
| **Value** | What to match | "Comedy", "2020", "7" |

### Common Fields

#### For TV Shows

| Field | Description | Example Use |
|-------|-------------|-------------|
| **Genre** | Content genre | Comedy, Drama, Documentary |
| **Year** | Release year | Shows from a specific era |
| **Rating** | Content rating | TV-14, TV-MA |
| **Studio** | Production studio | HBO, Netflix originals |
| **Tag** | Custom tags you've added | "Favorites", "Kids OK" |
| **Actor** | Cast members | Shows with specific actors |
| **Title** | Show name | Contains certain words |
| **Path** | File location | Shows from specific folders |
| **Date added** | When added to library | Recently added content |
| **Status** | Continuing/Ended | Only active shows |

#### For Movies

| Field | Description | Example Use |
|-------|-------------|-------------|
| **Genre** | Content genre | Action, Horror, Documentary |
| **Year** | Release year | Specific decade |
| **Rating** | User rating (1-10) | Highly rated only |
| **MPAA** | Content rating | PG, PG-13, R |
| **Studio** | Production studio | Marvel, Pixar |
| **Director** | Film director | Favorite directors |
| **Tag** | Custom tags | "Date Night", "Family" |
| **Runtime** | Length in minutes | Under 2 hours |
| **Set** | Collection membership | Part of a franchise |

### Operators

| Operator | Description | Example |
|----------|-------------|---------|
| **is** | Exact match | Genre is "Comedy" |
| **is not** | Exclude exact match | Genre is not "Horror" |
| **contains** | Partial match | Title contains "Star" |
| **does not contain** | Exclude partial | Title does not contain "Part" |
| **starts with** | Begins with text | Title starts with "The" |
| **ends with** | Ends with text | Title ends with "2" |
| **greater than** | Numeric comparison | Year greater than 1999 |
| **less than** | Numeric comparison | Runtime less than 120 |
| **in the last** | Date-based | Date added in the last 30 days |
| **true / false** | Boolean fields | Has trailer is true |

### Combining Rules

You can combine multiple rules:

| Combination | Effect |
|-------------|--------|
| **And** | Content must match ALL rules |
| **Or** | Content must match ANY rule |

**Example:** "Comedy AND Year > 2010" = Only comedies from 2011 onward

---

## Playlist File Format

Smart playlists are XML files with the `.xsp` extension. Here's the structure:

```xml
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<smartplaylist type="tvshows">
    <name>My Playlist Name</name>
    <match>all</match>
    <rule field="genre" operator="is">
        <value>Comedy</value>
    </rule>
</smartplaylist>
```

### Key Elements

| Element | Description |
|---------|-------------|
| `type` | "tvshows" or "movies" |
| `name` | Display name in Kodi |
| `match` | "all" (AND logic) or "one" (OR logic) |
| `rule` | Individual filter rule |
| `order` | Optional sorting |

### Multiple Values

A single rule can have multiple values (OR within the rule):

```xml
<rule field="genre" operator="is">
    <value>Comedy</value>
    <value>Sitcom</value>
</rule>
```

This matches shows that are Comedy OR Sitcom.

---

## Playlist Location

Kodi stores smart playlists in:

```
special://profile/playlists/video/
```

**Actual paths:**
- **Windows:** `%APPDATA%\Kodi\userdata\playlists\video\`
- **Linux:** `~/.kodi/userdata/playlists/video/`
- **macOS:** `~/Library/Application Support/Kodi/userdata/playlists/video/`
- **LibreELEC/OSMC:** `/storage/.kodi/userdata/playlists/video/`

You can:
- Create playlists in Kodi's UI (saved automatically)
- Copy `.xsp` files directly to this folder
- Edit `.xsp` files with a text editor

---

## Apply Show Filter to Smart Playlists

If you use a show filter (Settings → Shows → Show Filter) and also generate auto-created smart playlists, you can connect them: enable **Apply show filter to smart playlists** in Settings → Advanced → Background Service. When enabled, only shows matching your filter will appear in the auto-created Episode and TVShow playlists. This is especially useful when combined with the [Power User Pattern](clones.md#power-user-pattern-main-as-service-clones-as-entry-points) of using the main addon as a service and clones as entry points.

---

## Combining with EasyTV Settings

Smart playlists are just one layer of filtering. EasyTV applies additional filters on top:

```
Your Library
    ↓
Smart Playlist Filter (if enabled)
    ↓
Duration Filter (if enabled)
    ↓
Premiere Settings (series/season premieres)
    ↓
Episode Selection (unwatched/watched/both)
    ↓
Final Result
```

### Example Combinations

| Goal | Smart Playlist | EasyTV Settings |
|------|----------------|-----------------|
| Short comedy episodes | Genre: Comedy | Duration max: 30 min |
| New drama only | Genre: Drama | Premieres: On, Watched: Off |
| 90s movies, no horror | Year: 1990-1999, Genre ≠ Horror | Movie selection: Any |
| Highly-rated unwatched | Rating > 7 | Selection: Unwatched only |
| Kids content under 25 min | Tag: "Kids OK" | Duration max: 25 min |

---

## Power User Scenarios

### Scenario 1: Multiple "Channels"

Create different EasyTV experiences using [clones](clones.md):

| Clone | Smart Playlist | Use Case |
|-------|----------------|----------|
| EasyTV Comedy | Comedy shows only | Light entertainment |
| EasyTV Drama | Drama + Thriller | Serious viewing |
| EasyTV Kids | Kids-tagged content | Family friendly |

### Scenario 2: Seasonal Watching

Create playlists for different moods:

| Season | Smart Playlist |
|--------|----------------|
| Halloween | Genre: Horror, Thriller |
| Christmas | Tag: "Holiday" |
| Summer | Genre: Comedy, Adventure |

### Scenario 3: Catch-Up Queue

Smart playlist: "Date added in last 14 days"
- Always watch your newest content first
- Combines with EasyTV's partial prioritization

### Scenario 4: Quality Filter

Smart playlist: "User rating > 7"
- Only watch content you've rated highly
- Great for rewatching favorites

---

## Troubleshooting Playlists

### Playlist Not Appearing

- Ensure the `.xsp` file is in the correct folder
- Check the file extension is `.xsp` (not `.xsp.txt`)
- Verify the `type` attribute matches what you're filtering (tvshows/movies)
- Restart Kodi after adding new playlists

### No Content Matches

- Test the playlist in Kodi's library first (Videos → Playlists)
- Check if rules are too restrictive
- Verify your library has content matching the criteria
- Look for typos in genre names or values

### Wrong Content Type

EasyTV requires the right playlist type for each slot:
- TV show filter requires `type="tvshows"`
- Movie filter requires `type="movies"`

The selection dialog filters available playlists to the correct type before showing them, so picking the wrong one through the UI is normally not possible. If a TV filter slot has no entries to choose from, the dialog displays "No TV show playlists found" (and the same for movies). The mismatch can only occur if a `.xsp` path was edited manually in Kodi's settings file, or if a playlist's `type` attribute was changed after EasyTV stored its path.

---

## Related Pages

- **[Smart Playlist Examples](smart-playlist-examples.md):** Ready-to-use playlist files
- **[Settings Reference](settings-reference.md):** All filtering settings
- **[Advanced Features](advanced-features.md):** Clone feature for multiple configs
- **[Random-Order Shows](random-order-shows.md):** Another way to customize content
