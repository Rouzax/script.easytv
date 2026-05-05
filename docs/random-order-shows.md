# Random-Order Shows

> **Configured under** **Settings → Shows → Random Episode Order → Select shows for random order...**

Some TV shows don't need to be watched in order. Sitcoms, cartoons, sketch comedy, anthology series: these are "shuffle-friendly" shows where any episode works.

EasyTV lets you mark these shows for random episode selection instead of sequential viewing.

---

## What Are Random-Order Shows?

For most shows, EasyTV tracks your progress and plays the next episode in sequence:
- You watch Breaking Bad S02E05
- EasyTV suggests S02E06

For **random-order shows**, EasyTV picks any available episode:
- You're watching The Simpsons
- EasyTV picks a random unwatched episode (maybe S08E14, then S03E07, then S15E02)

---

## Good Candidates for Random Order

| Show Type | Examples | Why Random Works |
|-----------|----------|------------------|
| **Sitcoms** | Friends, Seinfeld, The Office | Episodes are mostly standalone |
| **Cartoons** | The Simpsons, Family Guy, South Park | Self-contained stories |
| **Sketch Comedy** | SNL, Key & Peele, MadTV | No continuity between episodes |
| **Anthology Series** | Black Mirror, Twilight Zone | Each episode is independent |
| **Reality/Competition** | Chopped, Forged in Fire | Episodes don't build on each other |
| **Late Night** | Talk shows, variety shows | Standalone episodes |

---

## Configuring Random-Order Shows

### Adding Shows to Random Order

1. Go to **Settings → Shows → Random Episode Order**
2. Click **Select shows for random order...**
3. A selection dialog opens with all your TV shows
4. Check the shows you want to randomize
5. Click **Save**

### Removing Shows from Random Order

1. Same path: **Settings → Shows → Random Episode Order**
2. Click **Select shows for random order...**
3. Uncheck shows you want to return to sequential order
4. Click **Save**

### Display

The settings show how many shows are marked for random order:
- "3 shows selected" (or however many)
- "No shows selected" if none

---

## How Random Order Works

### In Browse Mode

When a random-order show appears in the episode list:
- The displayed episode is random (not necessarily the "next" one)
- Each time you refresh, it may show a different episode
- Clicking plays that random episode

### In Random Playlist

When a random-order show is picked for the playlist:
- A random unwatched episode is selected
- Not the sequential "next" episode

### Episode Pool

Random selection draws from:
- **Unwatched mode:** All unwatched episodes
- **Watched mode:** All watched episodes
- **Both mode:** Mix based on your ratio setting

---

## Interaction with Episode Selection

The **Episode selection** setting (Unwatched/Watched/Both) affects random-order shows differently than sequential shows:

### Unwatched Only

| Sequential Shows | Random-Order Shows |
|------------------|-------------------|
| Next episode in order (S02E06) | Random unwatched episode |
| Progress advances linearly | Progress is scattered |

Both kinds of shows draw only from unwatched episodes. The difference is *which* unwatched episode is picked.

### Watched Only

| Sequential Shows | Random-Order Shows |
|------------------|-------------------|
| Random rewatch | Random rewatch |
| Same behavior | Same behavior |

No difference. Both pick randomly from watched episodes.

### Both (Mixed)

| Sequential Shows | Random-Order Shows |
|------------------|-------------------|
| Unwatched: Next in order | Unwatched: Random unwatched |
| Watched: Random rewatch | Watched: Random rewatch |

The "Unwatched episode chance" slider applies to both:
- 80% chance = mostly unwatched content
- For sequential: 80% chance of next episode, 20% chance of random rewatch
- For random-order: 80% chance of random unwatched, 20% chance of random rewatch

---

## Hiding from Browse Mode

If you only want random-order shows in random playlists (not the browse list):

1. Go to **Settings → Browse Mode → Appearance**
2. Enable **Hide random-order shows**

When enabled:
- Random-order shows don't appear in the episode list
- They still appear in random playlists
- Useful for shows you never manually pick

---

## Multiple Episodes Per Show

When **Allow multiple episodes of same TV Show** is enabled in Random Playlist settings:

### Sequential Shows
- First appearance: S02E06
- Second appearance: S02E07
- Third appearance: S02E08

### Random-Order Shows
- First appearance: Random episode A
- Second appearance: Random episode B (different from A)
- Third appearance: Random episode C (different from A and B)

Each appearance picks a different random episode (avoiding repeats within the playlist).

---

## Immediate Effect

When you add a show to random order:
- The change takes effect immediately
- In Browse Mode, the episode display updates on next refresh
- In Random Playlist, the next playlist uses random selection

When you remove a show from random order:
- EasyTV returns to sequential tracking
- It resumes from where you left off in the sequence

---

## Use Case Examples

### "Background Simpsons"

1. Add The Simpsons to random-order shows
2. Set EasyTV to Random Playlist mode
3. Include only The Simpsons (via show filter)
4. Launch and let random episodes play

### "Mixed Comedy Night"

1. Add sitcoms to random-order shows (Friends, Seinfeld, Parks & Rec)
2. Keep drama shows sequential
3. Use smart playlist filter for Comedy genre
4. Random playlist mixes random sitcom episodes

### "Anthology Exploration"

1. Add Black Mirror to random-order shows
2. Every episode is independent anyway
3. Let EasyTV pick which story you watch next

### "Kids Cartoon Channel"

1. Create EasyTV clone called "Kids TV"
2. Add all cartoons to random-order
3. Filter to Animation genre
4. Set to Random Playlist on launch
5. Kids press one button, random cartoons play

---

## Multi-Instance Sync Note

If you use [multi-instance sync](multi-instance-sync.md), configure your random-order shows **identically on all devices**. Random-order shows pick a different episode than sequential shows, so mismatched selections will cause devices to disagree on the next episode for affected shows.

---

## Technical Details

### What Gets Randomized

- Episode selection within a show
- NOT show selection (that's separate randomization in playlist building)

### Playback Tracking

- Watched episodes are still tracked normally
- Resume points work the same
- Progress just doesn't follow sequential order

### Multi-Episode in Both Mode

When using "Both" with "Allow multiple episodes" enabled, random-order shows in lazy queue mode:
- Each appearance recalculates which random episode to pick
- Avoids repeating the same episode within one playlist
- Respects the unwatched/watched ratio

---

## Troubleshooting

### Show Still Playing Sequentially

- Verify the show is checked in the random-order selection
- Refresh the browse list or generate a new playlist
- Check that you clicked "Save" after selecting

### Same Episode Keeps Appearing

- This can happen if you have very few unwatched episodes
- The pool of available episodes determines randomness
- Check your Episode Selection setting (Unwatched vs Both)

### Random-Order Show Missing from List

- Check if "Hide random-order shows" is enabled in Browse Mode settings
- The show should still appear in random playlists

---

## Related Pages

- **[Browse Mode](browse-mode.md):** How random-order shows appear in the list
- **[Random Playlist Mode](random-playlist-mode.md):** How random-order affects playlists
- **[Settings Reference](settings-reference.md):** All related settings
- **[Smart Playlist Integration](smart-playlist-integration.md):** Combine with genre filtering
