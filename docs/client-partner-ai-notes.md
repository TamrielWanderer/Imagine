# Client partner (demon) AI: reverse-engineering notes

Target: ReIMAGINE `ImagineClient.exe` (PE32, MSVC 7.1, image base 0x400000,
23,429,120 bytes, dated 2020-12-17). Not packed; RTTI class names are present,
so classes can be found from their type descriptors (`.?AV<name>@@`).
Addresses below are virtual addresses in that exact file.

## Classes

| Class | vtable | Notes |
| --- | --- | --- |
| `MiPartnerAITask` | 0x16ce49c | Demon brain. Constructor at ~0x636040 (name "PartnerAI"). |
| `MiPartnerActivateTask` | 0x16ceb04 | Walks the demon into range of its target, then hands over (messages 99 / 0x151). |
| `MiPartnerFollowTask` | 0x16cebb0 | Following the owner. |
| `MiCommandSkillActivate` | 0x16ced40 | Skill activation command. |

Tasks talk through messages (id at message+4). Functions are reached through
incremental-link thunks (`jmp`), e.g. vtable entry 0x43d456 -> 0x639ce0.

## MiPartnerAITask fields (this = demon AI task)

| Offset | Meaning (inferred) |
| --- | --- |
| +0x9c | owner character entity ID |
| +0xa0 | partner demon entity ID |
| +0xa4 | current target entity ID (<1 = none) |
| +0xb0 | chosen action (7 dwords), written by the skill picker |
| +0xfa | state: 3 idle/follow, 5 waiting after an action, ... |
| +0xf0 / +0xf4 | timers (ms) for the next decision / follow refresh (+1500) |
| +0x98 | in-combat flag (set by message 0x21, cleared by 0x1d) |
| +0x121..+0x12d | per-category enable flags (13 categories, see picker) |
| +0x12f..+0x135 | AI options, default 1,1,1,1,1,1,0 (copied from 0x87fe588) |
| +0x12f | "fight what the owner fights": with 1, enemies the owner attacks or targets become the demon's target (messages 0x92/0x93); with 0 only enemies the demon itself hits |
| +0x136 | u16, default 0xff |

## Functions

- 0x631df0 Initialize: resets fields, loads the option defaults.
- 0x639ce0 Update (periodic): leaves early unless in combat and active;
  re-targets every 15000 ms (`+0xe8 + 15000`); state machine on +0xfa;
  follow refresh every 1500 ms.
- 0x6340d0 ReceiveMessage: target selection. 0x92 owner targets an enemy,
  0x93 an entity was hit (attacker in +0x1c), 0x65 demon/owner was hit,
  0x8c..0x8f action results, 0x95 skill finished (wait 1500 ms), 0x10f /
  0x115 / 0x1c6 cooldown-like waits of 2000 / 5000 / 1500 ms.
- 0x636ee0 Skill picker: lists the demon's skills, then walks categories
  1..13 in a fixed order and stops at the first category that yields a
  skill (`do { ... } while (cat < 0xe)`, break when a candidate is set).
  A category is only tried if its flag at +0x120+cat is set. Distance
  thresholds: 2500.0 (0x16ce494, max range considered) and 500.0
  (0x16ce180, near/far split choosing builder 0x402d65 or 0x401519).
  Result copied to +0xb0.
- 0x639230 Acts on the picked action per demon type (+0x2e0 of the demon
  data selects the branch).

## Why the demon feels passive (working theory)

The picker is first-match by category, so whichever early category has a
usable skill always wins and later ones (often the stronger attacks) are
never reached. Re-targeting waits up to 15 s, and after each action the AI
waits 1.5 to 5 s.

## Next steps

1. Name the 13 categories (decompile builders 0x401519 / 0x402d65 and the
   remaining cases of 0x636ee0).
2. Candidate patches: shorter wait constants (1500/2000/5000/15000 ms),
   reordering or scoring categories instead of first-match, larger 2500.0
   engagement range.
3. Ship as a patched ImagineClient.exe (or byte patches applied by a
   script) through the launcher updater.
