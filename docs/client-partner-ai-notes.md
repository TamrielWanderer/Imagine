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

## Skill picker categories (0x636ee0)

Loop counter is the byte at [esp+0x54] (starts at 1, 0x6371b6); the tail at
0x638aa1 increments it up to 13. Jump table 0x638ad8. Each case builds a
candidate with 0x402d65 (target nearer than 500) or 0x401519 (farther,
up to 2500), passing the category number, so the category decides which of
the demon's skills qualify.

| Cat | Checks (inferred) |
| --- | --- |
| 1, 2 | owner / current target, by distance and status effects |
| 3, 4, 8, 9 | no handler (skipped) |
| 5 | party members in state 6 (dead): revive |
| 6 | party members with an ailment (+700): cure |
| 7 | party members below 60% HP (0.6 at 0x16cc424): heal |
| 10 | the demon's own status effects |
| 11 | self skills, no target needed |
| 12 | attack the current target (+0xa4) |
| 13 | owner support near the owner |

## Why the demon feels passive (working theory)

The picker is first-match by category, so whichever early category has a
usable skill always wins and later ones (often the stronger attacks) are
never reached. Re-targeting waits up to 15 s, and after each action the AI
waits 1.5 to 5 s.

## Choosing the skill inside a category

Builders 0x636b50 (near, weights at table+4) and 0x636ce0 (far, table+0x38)
pick one of 11 skill groups by weighted random. Weights come from the AI
data table (`func(0x103)`), indexed [category*26 + group]; a group only
counts if its AI option is on: option index = byte table 0x87fe590[group]
= 1,1,1,2,3,3,3,4,4,4,5, read as `this+0x12f+index`. 0x636490 then lists the
demon's skills of that group from the list at +0x10c (entries of 0x1c bytes:
+4 = skill action type, +7 = support sub-type, +8.. status IDs):

| Group | Action type |
| --- | --- |
| 0, 1, 2 | ATTACK, SPIN, RUSH |
| 3 | SHOT or RAPID |
| 4, 5, 6 | GUARD, COUNTER, DODGE |
| 7, 8, 9, 10 | SUPPORT sub-types 7, 8 (cure a status), 9, 10 |

Nothing in this path looks at the target's affinities, which is why the
demon can attack with an element the enemy drains.

## Applied patches (contrib/client-patches/partner_ai_patch.py)

- Six pause/retarget constants shortened.
- Category order changed to 5,6,7,1,2,12,10,11,13 (attack before self
  skills and owner buffs): the loop tail jumps to a cave at 0x638b20 that
  reads the next category from a 14-byte table at 0x638b40.
- Groups 4-6 (guard/counter/dodge) now use option index -0x30, i.e. the
  flag at +0xff that message 0x8e sets while the target is starting an
  attack, so the demon only defends when an attack is coming.
- Learning affinities: action reports are handled in 0x68d300 (entries at
  report+0x68, skill at +8) and 0x690970 (entries at +0x88, skill at +0xc);
  entries are 0x68 bytes: +4 target, +0xc damage type 1, +0x14 type 2,
  +0x16 u16 result flags. Hooks at 0x68e342 / 0x6917c6 (reached for hits by
  the owner or partner) record (target, skill) when the result is healing
  (1) or drain (5) on the target, or flags 0x3e00 (reflect/null/absorb),
  into a 32-entry ring at 0x8912f00 (unused tail of .rwdata). The skill
  list push in the picker pre-pass (call at 0x637093, ecx = task+0x10c)
  goes through a filter that drops a skill recorded for the current target
  (task+0xa4). Code at 0x638b60..0x638c20, from build_learning_cave.py.
- Aggressive mode: AI option index 3 (byte +0x132, the old "defense"
  option) off = aggressive. Hook at 0x639d1a in Update (after the
  active/enabled checks, esi = task) calls code at 0x638c30: if option off
  and no target, it walks the entity manager's id table (task 0x100 +
  0x98; hash table: +4 bucket count, +8 buckets, node {next, id, value}),
  keeps entities whose data +0x5f == 3 (enemy), hostile (0x40c2ed == 1),
  not in state 5 (0x42b1de +8), and picks the nearest within 1500 units
  (positions from 0x41bbc1). Then sets +0xa4, +0xfa = 3, +0x103 = 1 and
  +0xe8 = now, like the "owner targets an enemy" handler (0x634441).
  Scratch at 0x8912e80. Verified in an emulator with stubbed game calls.
- Skill data: data manager task 0x103, vtable +0x18 = get skill by ID
  (thiscall). The record mirrors the libhack MiSkillData schema with C
  alignment and 12-byte std::list members: +0x8 affinity, +0x19 action
  type, +0x40 charge time, +0x50 target range (u16), +0x52 target type,
  +0x68 area type, +0x69 valid type, +0x6c aoe range, +0x78 modifier 1,
  +0x94 head of the add-status list.
- Skill filter v2 at 0x638f80 (build_skill_filter.py) replaces the first
  filter: also drops untargeted attacks around the demon (target type 0,
  valid ENEMY, area 3/9/4/5) while the target is farther than
  aoeRange*10+150.
- comp_client.dll's expected SHA-1 of .text updated to match.

## Next steps

1. Name the 13 categories (decompile builders 0x401519 / 0x402d65 and the
   remaining cases of 0x636ee0).
2. Candidate patches: shorter wait constants (1500/2000/5000/15000 ms),
   reordering or scoring categories instead of first-match, larger 2500.0
   engagement range.
3. Ship as a patched ImagineClient.exe (or byte patches applied by a
   script) through the launcher updater.
