# Stephen's Clock: rogue-like dungeon runs

Stephen's Clock is an item with ten tiers, I to X. A player winds one, opens a dungeon, and that dungeon becomes a **clock run**: tougher enemies scaled to the party, random rules, a countdown, and better rewards while the countdown lasts. Clearing the dungeon in time gives the next tier.

Code: `server/channel/src/StephensClock.cpp`. Effects: `datastore/data/tokusei/tokusei_stephens_clock.xml`. Client data: `contrib/roguelike/stephens_clock_data.py`.

## For players

1. **Get a clock.** Bosses of level 70 and higher in normal dungeons have an 8% chance to drop **Stephen's Clock I**.
2. **Wind it.** Use the clock from the inventory, anywhere. It stays in the inventory. Use it again to unwind it. Winding is forgotten when you log out.
3. **Open a dungeon.** The next dungeon you create becomes the clock run, and the clock is used up when the first player enters. One clock covers the whole party.
4. **Beat the countdown.** You start with 25 minutes. Every boss kill adds 4 minutes, every player death takes 2 minutes away.
5. **Clear the dungeon.** When the final boss room is empty, the player who used the clock receives the next tier (tier X gives another X).

If the countdown ends first, the dungeon stays as it is and can still be finished, but its rewards go back to normal and no clock is given.

Commands, for every player:

| Command | What it does |
| --- | --- |
| `@clock` | Shows the run: tier, time left, rules, boons. Outside a run it shows whether a clock is wound. |
| `@boon N` | Chooses boon N when the clock offers three. |

### Tiers

Difficulty and reward grow by the same step each tier.

| Tier | Enemy level (from the party's highest) | Enemy HP | Enemy damage | XP | Macca, Magnetite | Drop rate | Rules |
| --- | --- | --- | --- | --- | --- | --- | --- |
| I | -5 | +15% | +5% | +20% | +20% | +10% | 1 |
| II | -4 | +30% | +10% | +40% | +40% | +20% | 1 |
| III | -3 | +45% | +15% | +60% | +60% | +30% | 1 |
| IV | -2 | +60% | +20% | +80% | +80% | +40% | 2 |
| V | -1 | +75% | +25% | +100% | +100% | +50% | 2 |
| VI | 0 | +90% | +30% | +120% | +120% | +60% | 2 |
| VII | +1 | +105% | +35% | +140% | +140% | +70% | 2 |
| VIII | +2 | +120% | +40% | +160% | +160% | +80% | 3 |
| IX | +3 | +135% | +45% | +180% | +180% | +90% | 3 |
| X | +4 | +150% | +50% | +200% | +200% | +100% | 3 |

- The enemy level is a floor: enemies that are already higher keep their level, and no enemy goes above 99. The party's highest level is taken when the run starts.
- Every player after the first adds +30% enemy HP (up to +120%).
- Bosses also carry extra Macca and Magnetite that grows with the tier and the boss level.

### Rules

One to three rules are rolled when the run starts. They change the fight for everyone instead of forbidding anything, so every build can play every rule.

| Rule | Effect |
| --- | --- |
| Blazing, Frozen, Thunder, Gale Hour | Fire, Ice, Electric or Force damage +50% for everyone |
| Hour of Steel, Powder, Sorcery | Close-range, long-range or spell damage +40% for everyone |
| Swift, Mighty, Arcane, Guarded Demons | Every demon (enemies and partner demons) has the effect of full Sukukaja, Tarukaja, Makakaja or Rakukaja at all times |
| Hour of Haste | Chant and cooldown times -30% for everyone |
| Killing Hour | Critical hits are much more likely for everyone |
| Hour of Vigor | HP and MP regenerate 3x faster for everyone |
| Glass Hour | Everyone deals +35% damage |
| Fleet Hour | Everyone moves 25% faster |
| Golden Hour | Enemies have +30% HP; Macca and Magnetite +60% |
| Scholar's Hour | Enemies deal +15% damage; XP +60% |

The elemental bonuses add to the game's normal affinity boost, which is capped at +100% in total.

### Boons

After every 20 enemies and after every boss that isn't the last one, the clock offers three boons. Anyone in the run chooses one with `@boon N`. It lasts for the run, applies to the whole party and their demons, and the same boon can be taken again. An offer nobody answers is settled with its first choice when the next one comes.

Might (+12% damage), Aegis (-10% damage taken), Vitality (+20% max HP), Spirit (+20% max MP, faster MP regeneration), Focus (chant and cooldown -10%), Precision (more critical hits), Fleetness (+15% speed), Fortune (+25% Macca and Magnetite), Insight (+25% XP), Borrowed Time (+5 minutes), Plunder (+15% drop rate).

## For the server owner

### Setup

1. Build the server (the feature is in `comp_channel`).
2. Run `scripts\stephens_clock_data.bat`. It adds the ten items and the countdown to the client data in `BinaryData\Shield` (`ItemData.sbin`, `CItemData.sbin`, `TimeLimitData.sbin`). `-Check` only reports, `-Remove` takes the entries out again.
3. Restart the server.
4. Publish the three files so every player has them: `scripts\publish_update.bat -Add BinaryData\Shield\ItemData.sbin,BinaryData\Shield\CItemData.sbin,BinaryData\Shield\TimeLimitData.sbin`

Run step 2 again after `apply_translation` or `stack_sizes`: both rebuild the item files from their own backups, which drops the clock items.

To test without farming, give yourself a clock with the GM command `@item 19001` (19001 is tier I, 19010 is tier X).

### Settings (`channel.xml`)

| Setting | Default | Meaning |
| --- | --- | --- |
| `StephensClock` | `true` | Turns the whole system on or off |
| `StephensClockItemID` | `19001` | Item ID of tier I; the next nine IDs are tiers II to X |
| `StephensClockTimerID` | `121` | `TimeLimitData` entry used for the countdown |
| `StephensClockTimerLength` | `3600` | Length of that entry in seconds; the clock can never show more |
| `StephensClockTime` | `1500` | Seconds on the clock at the start |
| `StephensClockBossTime` | `240` | Seconds added per boss kill |
| `StephensClockDeathPenalty` | `120` | Seconds lost per player death |
| `StephensClockDropLevel` | `70` | Boss level needed to drop Stephen's Clock I |
| `StephensClockDropRate` | `8.0` | Chance of that drop in percent (`0` turns it off) |
| `StephensClockDifficultyPercent` | `100` | Scales enemy HP and damage bonuses |
| `StephensClockRewardPercent` | `100` | Scales XP, Macca, Magnetite and drop bonuses |
| `StephensClockDenyInstances` | empty | Instance definition IDs that never become clock runs |

What each rule and boon does is data: edit `contrib/roguelike/make_tokusei.py`, run it, and restart the server. The names and descriptions players see are in `StephensClock.cpp`.

### Which dungeons work

A dungeon can be a clock run if it is a normal instance (not a time trial, demon-only dungeon, mission, PvP, Diaspora, Pentalpha or digitalize dungeon), has no timer of its own at creation, and has at least one spawn of category BOSS. 156 of the 373 instance definitions qualify. Anywhere else the clock says so and is not used up.

The run counts as cleared when a boss dies in the **final boss room** and no boss is alive there six seconds later. The final boss room is the last zone in the instance's zone list that has boss spawns. This is a rule of thumb: if a dungeon is judged wrong, add it to `StephensClockDenyInstances`.

### How it works

- **Winding** is kept on the client state (memory only). The item is not consumed on use.
- **Creation.** When a player with a wound clock creates an instance on this channel, the instance is marked as pending. When the first player enters, the clock is taken from the owner's inventory and the run starts, before the first zone and its enemies are built.
- **Enemies** get their level raised at spawn and stacked tokusei for HP and damage, plus the tokusei of the rolled rules.
- **Players** and their partner demons get tokusei for rewards, rules and boons when they enter a zone of the run and when a demon is summoned. They are cleared on leaving the instance, like other instance tokusei.
- **Drop rate** is a multiplier passed to the loot roll for enemy bodies and for chests created by dungeon events.
- **Countdown.** The client only counts down from the fixed length of a `TimeLimitData` entry, so the server reports a start time that leaves the time it wants. If the dungeon starts a timer of its own, that one takes the display and the clock keeps running in the background; `@clock` still shows it.
- **When the clock stops,** reward tokusei are removed, the drop multiplier goes back to 1, bosses stop carrying extra loot, and no more boons are offered. Enemy scaling and the rules stay.

### Limits

- An instance created on another channel (multi-channel setups) is not a clock run.
- The item reuses the icon of the Hourglass of Reversal and the unused item skill 11974.
- Text is English only; it is sent by the server as chat messages.
