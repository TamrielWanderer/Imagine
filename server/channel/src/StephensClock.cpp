/**
 * @file server/channel/src/StephensClock.cpp
 * @ingroup channel
 *
 * @brief Stephen's Clock: rogue-like dungeon runs.
 *
 * This file is part of the Channel Server (channel).
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU Affero General Public License as
 * published by the Free Software Foundation, either version 3 of the
 * License, or (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU Affero General Public License for more details.
 *
 * You should have received a copy of the GNU Affero General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 */

#include "StephensClock.h"

// libcomp Includes
#include <DefinitionManager.h>
#include <Log.h>
#include <PacketCodes.h>
#include <Randomizer.h>
#include <ServerConstants.h>
#include <ServerDataManager.h>

// object Includes
#include <ChannelConfig.h>
#include <EnemyBase.h>
#include <EntityStats.h>
#include <InstanceAccess.h>
#include <ItemDrop.h>
#include <MiTimeLimitData.h>
#include <ServerZone.h>
#include <ServerZoneInstance.h>
#include <ServerZoneInstanceVariant.h>
#include <Spawn.h>
#include <Tokusei.h>

// channel Includes
#include "ChannelClientConnection.h"
#include "ChannelServer.h"
#include "CharacterState.h"
#include "ClientState.h"
#include "DemonState.h"
#include "EnemyState.h"
#include "CharacterManager.h"
#include "ChatManager.h"
#include "ManagerConnection.h"
#include "TokuseiManager.h"
#include "Zone.h"
#include "ZoneInstance.h"
#include "ZoneManager.h"

// Standard C++11 Includes
#include <iterator>
#include <set>
#include <unordered_map>

using namespace channel;

namespace {

/// Unit tokusei, stacked to reach the tier's numbers
const int32_t TOKUSEI_ENEMY_HP = CLOCK_TOKUSEI_BASE + 1;      // +5% each
const int32_t TOKUSEI_ENEMY_DAMAGE = CLOCK_TOKUSEI_BASE + 2;  // +5% each
const int32_t TOKUSEI_XP = CLOCK_TOKUSEI_BASE + 11;           // +5% each
const int32_t TOKUSEI_MACCA = CLOCK_TOKUSEI_BASE + 12;        // +5% each

/// Modifier m uses CLOCK_TOKUSEI_BASE + 100 + m * 5 + slot. A slot only
/// applies if a tokusei with that ID is defined.
enum ModifierSlot : int32_t {
  SLOT_ALL = 0,      // Enemies, characters and partner demons
  SLOT_DEMONS = 1,   // Enemies and partner demons
  SLOT_ENEMIES = 2,  // Enemies
  SLOT_PLAYERS = 3,  // Characters and partner demons
  SLOT_REWARD = 4,   // Characters and partner demons, until the clock stops
};

/// Boon b uses CLOCK_TOKUSEI_BASE + 500 + b * 2 (+1 for reward boons that
/// stop when the clock stops)
const int32_t TOKUSEI_BOON = CLOCK_TOKUSEI_BASE + 500;

struct ClockText {
  const char* Name;
  const char* Desc;
};

// Modifiers change the rules for everyone instead of taking options away:
// any build can use them, some builds can use them better.
const ClockText MODIFIERS[] = {
    {"", ""},
    {"Blazing Hour", "Fire damage +50% for everyone"},
    {"Frozen Hour", "Ice damage +50% for everyone"},
    {"Thunder Hour", "Electric damage +50% for everyone"},
    {"Gale Hour", "Force damage +50% for everyone"},
    {"Hour of Steel", "Close-range damage +40% for everyone"},
    {"Hour of Powder", "Long-range damage +40% for everyone"},
    {"Hour of Sorcery", "Spell damage +40% for everyone"},
    {"Swift Demons", "All demons have permanent Sukukaja"},
    {"Mighty Demons", "All demons have permanent Tarukaja"},
    {"Arcane Demons", "All demons have permanent Makakaja"},
    {"Guarded Demons", "All demons have permanent Rakukaja"},
    {"Hour of Haste", "Chant and cooldown times -30% for everyone"},
    {"Killing Hour", "Critical hits are much more likely for everyone"},
    {"Hour of Vigor", "HP and MP regenerate 3x faster for everyone"},
    {"Golden Hour", "Enemies have +30% HP, Macca and Magnetite +60%"},
    {"Scholar's Hour", "Enemies deal +15% damage, XP +60%"},
    {"Glass Hour", "Everyone deals +35% damage"},
    {"Fleet Hour", "Everyone moves 25% faster"},
};
const uint8_t MODIFIER_COUNT =
    (uint8_t)(sizeof(MODIFIERS) / sizeof(MODIFIERS[0]) - 1);

enum Boon : uint8_t {
  BOON_TIME = 10,
  BOON_PLUNDER = 11,
};

const ClockText BOONS[] = {
    {"", ""},
    {"Might", "+12% damage"},
    {"Aegis", "-10% damage taken"},
    {"Vitality", "+20% max HP"},
    {"Spirit", "+20% max MP, MP regenerates faster"},
    {"Focus", "Chant and cooldown times -10%"},
    {"Precision", "Critical hits are more likely"},
    {"Fleetness", "+15% movement speed"},
    {"Fortune", "+25% Macca and Magnetite"},
    {"Insight", "+25% XP"},
    {"Borrowed Time", "+5 minutes on the clock"},
    {"Plunder", "+15% drop rate"},
};
const uint8_t BOON_COUNT = (uint8_t)(sizeof(BOONS) / sizeof(BOONS[0]) - 1);

const char* ROMAN[] = {"",   "I",   "II",   "III", "IV", "V",
                       "VI", "VII", "VIII", "IX",  "X"};

std::shared_ptr<objects::ChannelConfig> GetConf(
    const std::shared_ptr<ChannelServer>& server) {
  return server ? std::dynamic_pointer_cast<objects::ChannelConfig>(
                      server->GetConfig())
                : nullptr;
}

libcomp::String TimeString(uint64_t now, uint64_t expire) {
  uint32_t left = expire > now ? (uint32_t)((expire - now) / 1000000ULL) : 0;
  return libcomp::String("%1:%2%3")
      .Arg(left / 60)
      .Arg((left % 60) < 10 ? "0" : "")
      .Arg(left % 60);
}

bool IsBoss(const std::shared_ptr<objects::Spawn>& spawn) {
  return spawn && spawn->GetCategory() == objects::Spawn::Category_t::BOSS;
}

uint16_t Scale(uint32_t value, uint16_t percent) {
  uint32_t result = (value * (uint32_t)percent + 50) / 100;
  return (uint16_t)(result > 60000 ? 60000 : result);
}

}  // namespace

ClockTierValues StephensClock::GetTierValues(uint8_t tier, uint16_t difficulty,
                                             uint16_t reward) {
  if (tier < 1) {
    tier = 1;
  } else if (tier > CLOCK_MAX_TIER) {
    tier = CLOCK_MAX_TIER;
  }

  // Difficulty and reward grow together and linearly, so every tier is the
  // same step up from the one before and no tier is the "best deal":
  //   tier I : enemies 5 levels under the party, +15% HP, +5% damage
  //   tier X : enemies 4 levels over the party, +150% HP, +50% damage
  // The reward for that is +20% XP, +20% Macca/Magnetite and +10% drop
  // rate per tier.
  ClockTierValues v;
  v.LevelOffset = (int8_t)(tier - 6);
  v.EnemyHP = Scale((uint32_t)tier * 15, difficulty);
  v.EnemyDamage = Scale((uint32_t)tier * 5, difficulty);
  v.XP = Scale((uint32_t)tier * 20, reward);
  v.Macca = Scale((uint32_t)tier * 20, reward);
  v.Drops = Scale((uint32_t)tier * 10, reward);
  v.Modifiers = (uint8_t)(tier <= 3 ? 1 : (tier <= 7 ? 2 : 3));

  return v;
}

uint8_t StephensClock::GetItemTier(const std::shared_ptr<ChannelServer>& server,
                                   uint32_t itemID) {
  auto conf = GetConf(server);
  if (!conf || !conf->GetStephensClock() || !itemID) {
    return 0;
  }

  uint32_t first = conf->GetStephensClockItemID();
  if (itemID >= first && itemID < first + CLOCK_MAX_TIER) {
    return (uint8_t)(itemID - first + 1);
  }

  return 0;
}

void StephensClock::Tell(const std::shared_ptr<ChannelServer>& server,
                         const std::shared_ptr<ChannelClientConnection>& client,
                         const libcomp::String& message) {
  if (client) {
    server->GetChatManager()->SendChatMessage(
        client, ChatType_t::CHAT_SELF,
        libcomp::String("[Clock] %1").Arg(message));
  }
}

void StephensClock::TellAll(const std::shared_ptr<ChannelServer>& server,
                            const std::shared_ptr<ZoneInstance>& instance,
                            const libcomp::String& message) {
  for (auto client : instance->GetConnections()) {
    Tell(server, client, message);
  }
}

void StephensClock::UseItem(
    const std::shared_ptr<ChannelServer>& server,
    const std::shared_ptr<ChannelClientConnection>& client, uint32_t itemID) {
  uint8_t tier = GetItemTier(server, itemID);
  if (!client || !tier) {
    return;
  }

  auto state = client->GetClientState();
  if (state->GetClockArmedItem() == itemID) {
    state->SetClockArmedItem(0);
    Tell(server, client,
         libcomp::String("Stephen's Clock %1 is no longer wound.")
             .Arg(ROMAN[tier]));
    return;
  }

  state->SetClockArmedItem(itemID);

  auto v = GetTierValues(tier);
  Tell(server, client,
       libcomp::String("Stephen's Clock %1 is wound. It is used up when you "
                       "enter the next dungeon you open.")
           .Arg(ROMAN[tier]));
  Tell(server, client,
       libcomp::String("Enemies: level %1%2 from your party's highest, +%3% "
                       "HP, +%4% damage, %5 random rule%6.")
           .Arg(v.LevelOffset >= 0 ? "+" : "")
           .Arg((int32_t)v.LevelOffset)
           .Arg(v.EnemyHP)
           .Arg(v.EnemyDamage)
           .Arg(v.Modifiers)
           .Arg(v.Modifiers == 1 ? "" : "s"));
  Tell(server, client,
       libcomp::String("Rewards: +%1% XP, +%2% Macca and Magnetite, +%3% "
                       "drops. Use the clock again to unwind it.")
           .Arg(v.XP)
           .Arg(v.Macca)
           .Arg(v.Drops));
}

void StephensClock::InstanceCreated(
    const std::shared_ptr<ChannelServer>& server,
    const std::shared_ptr<ChannelClientConnection>& client,
    const std::shared_ptr<ZoneInstance>& instance) {
  auto conf = GetConf(server);
  if (!conf || !conf->GetStephensClock() || !client || !instance) {
    return;
  }

  auto state = client->GetClientState();
  uint32_t itemID = state->GetClockArmedItem();
  uint8_t tier = GetItemTier(server, itemID);
  if (!tier) {
    return;
  }

  auto def = instance->GetDefinition();
  auto variant = instance->GetVariant();

  // Only plain dungeons: special modes have their own timers and rewards
  bool valid =
      def &&
      (!variant ||
       variant->GetInstanceType() ==
           objects::ServerZoneInstanceVariant::InstanceType_t::NORMAL) &&
      !instance->GetTimeLimitData() &&
      !conf->StephensClockDenyInstancesContains(def->GetID());

  // The run is cleared when the boss of the final room falls. The final
  // room is the last zone of the instance that has enemies at all. Many
  // dungeons get their enemies from zone partials (shared by all of their
  // zones), so those have to be applied before looking.
  uint32_t finalZoneID = 0, finalDynamicMapID = 0;
  if (valid) {
    auto serverDataManager = server->GetServerDataManager();
    for (size_t i = 0; i < def->ZoneIDsCount() && i < def->DynamicMapIDsCount();
         i++) {
      auto zoneDef = serverDataManager->GetZoneData(
          def->GetZoneIDs(i), def->GetDynamicMapIDs(i), true);
      if (zoneDef && zoneDef->SpawnsCount() > 0) {
        finalZoneID = def->GetZoneIDs(i);
        finalDynamicMapID = def->GetDynamicMapIDs(i);
      }
    }

    valid = finalZoneID != 0;
  }

  if (!valid) {
    LogZoneManagerWarning([&]() {
      return libcomp::String(
                 "Stephen's Clock: instance %1 (variant %2) cannot be a clock "
                 "run\n")
          .Arg(instance->GetDefinitionID())
          .Arg(variant ? variant->GetID() : 0);
    });

    Tell(server, client,
         "Stephen's Clock does not react to this place. It stays wound and "
         "was not used up.");
    return;
  }

  Tell(server, client,
       libcomp::String("Stephen's Clock %1 answers this dungeon. The run "
                       "starts when you enter.")
           .Arg(ROMAN[tier]));

  instance->SetClockPendingTier(tier);
  instance->SetClockItemID(itemID);
  instance->SetClockOwnerCID(state->GetWorldCID());
  instance->SetClockFinalZoneID(finalZoneID);
  instance->SetClockFinalDynamicMapID(finalDynamicMapID);
}

void StephensClock::InstanceEntering(
    const std::shared_ptr<ChannelServer>& server,
    const std::shared_ptr<ZoneInstance>& instance) {
  if (!instance || !instance->GetClockPendingTier()) {
    return;
  }

  uint8_t tier = instance->GetClockPendingTier();
  instance->SetClockPendingTier(0);

  auto conf = GetConf(server);
  if (!conf || instance->GetAccessed() || instance->GetClockTier()) {
    return;
  }

  // The clock is used up now, from the player who wound it
  auto owner = server->GetManagerConnection()->GetEntityClient(
      instance->GetClockOwnerCID(), true);
  if (!owner) {
    LogZoneManagerWarningMsg(
        "Stephen's Clock: the player who wound the clock is not on this "
        "channel, no run started\n");
    return;
  }

  auto ownerState = owner->GetClientState();
  uint32_t itemID = instance->GetClockItemID();
  if (ownerState->GetClockArmedItem() != itemID) {
    Tell(server, owner,
         "Your Stephen's Clock is no longer wound. This is a normal "
         "dungeon.");
    return;
  }

  ownerState->SetClockArmedItem(0);

  std::unordered_map<uint32_t, uint32_t> cost;
  cost[itemID] = 1;
  if (!server->GetCharacterManager()->AddRemoveItems(owner, cost, false)) {
    Tell(server, owner,
         "You no longer carry the Stephen's Clock you wound. This is a "
         "normal dungeon.");
    return;
  }

  // Scale to the strongest player that can enter
  int8_t level = 1;
  uint8_t partySize = 0;
  for (auto client : server->GetManagerConnection()->GetEntityClients(
           instance->GetOriginalAccessCIDs(), true)) {
    auto cState = client->GetClientState()->GetCharacterState();
    if (cState && cState->GetLevel() > level) {
      level = cState->GetLevel();
    }

    partySize++;
  }

  if (partySize < 1) {
    partySize = 1;
  }

  auto v = GetTierValues(tier, conf->GetStephensClockDifficultyPercent(),
                         conf->GetStephensClockRewardPercent());

  // Roll the rules of this run
  std::set<uint8_t> rolled;
  while (rolled.size() < v.Modifiers && rolled.size() < MODIFIER_COUNT) {
    rolled.insert((uint8_t)RNG(uint16_t, 1, (uint16_t)MODIFIER_COUNT));
  }

  instance->ClearClockModifiers();
  for (uint8_t m : rolled) {
    instance->AppendClockModifiers(m);
  }

  instance->SetClockLevel((uint8_t)level);
  instance->SetClockPartySize(partySize);
  instance->SetClockBossKills(0);
  instance->SetClockExpired(false);
  instance->SetClockComplete(false);
  instance->SetClockTier(tier);

  if (!server->GetDefinitionManager()->GetTokuseiData(TOKUSEI_ENEMY_HP)) {
    LogZoneManagerErrorMsg(
        "Stephen's Clock: datastore/data/tokusei/tokusei_stephens_clock.xml "
        "is not loaded, clock runs will have no effects\n");
  }

  LogZoneManagerWarning([&]() {
    return libcomp::String(
               "Stephen's Clock %1 run started in instance %2 (%3), party "
               "level %4, %5 player(s)\n")
        .Arg(tier)
        .Arg(instance->GetID())
        .Arg(instance->GetDefinitionID())
        .Arg((int32_t)level)
        .Arg(partySize);
  });

  SetExpire(server, instance,
            ChannelServer::GetServerTime() +
                (uint64_t)conf->GetStephensClockTime() * 1000000ULL);
}

bool StephensClock::IsRun(const std::shared_ptr<ZoneInstance>& instance) {
  return instance && instance->GetClockTier() > 0;
}

bool StephensClock::IsRewarding(const std::shared_ptr<ZoneInstance>& instance) {
  return IsRun(instance) && !instance->GetClockExpired();
}

int8_t StephensClock::GetEnemyLevel(
    const std::shared_ptr<Zone>& zone,
    const std::shared_ptr<objects::Spawn>& spawn, bool asAlly, int8_t level) {
  auto instance = zone ? zone->GetInstance() : nullptr;
  if (!IsRun(instance) || asAlly ||
      (spawn && spawn->GetCategory() == objects::Spawn::Category_t::ALLY)) {
    return level;
  }

  // Enemies are never weaker than the dungeon made them, so a clock in a
  // dungeon above the party's level is not a shortcut
  int32_t minLevel = (int32_t)instance->GetClockLevel() +
                     GetTierValues(instance->GetClockTier()).LevelOffset;
  if (minLevel > 99) {
    minLevel = 99;
  }

  return (int32_t)level < minLevel ? (int8_t)minLevel : level;
}

void StephensClock::ApplyToEnemy(
    const std::shared_ptr<ChannelServer>& server,
    const std::shared_ptr<Zone>& zone,
    const std::shared_ptr<ActiveEntityState>& eState,
    const std::shared_ptr<objects::Spawn>& spawn, bool asAlly) {
  auto instance = zone ? zone->GetInstance() : nullptr;
  auto conf = GetConf(server);
  if (!IsRun(instance) || !eState || !conf || asAlly ||
      (spawn && spawn->GetCategory() == objects::Spawn::Category_t::ALLY)) {
    return;
  }

  auto definitionManager = server->GetDefinitionManager();
  auto v = GetTierValues(instance->GetClockTier(),
                         conf->GetStephensClockDifficultyPercent(),
                         conf->GetStephensClockRewardPercent());

  // More players means more damage: +30% HP for each one after the first
  uint32_t extra = instance->GetClockPartySize() > 1
                       ? (uint32_t)(instance->GetClockPartySize() - 1)
                       : 0;
  if (extra > 4) {
    extra = 4;
  }

  uint16_t hpStacks = (uint16_t)((v.EnemyHP + extra * 30 + 2) / 5);
  uint16_t dmgStacks = (uint16_t)((v.EnemyDamage + 2) / 5);
  if (hpStacks && definitionManager->GetTokuseiData(TOKUSEI_ENEMY_HP)) {
    eState->SetAdditionalTokusei(TOKUSEI_ENEMY_HP, hpStacks);
  }

  if (dmgStacks && definitionManager->GetTokuseiData(TOKUSEI_ENEMY_DAMAGE)) {
    eState->SetAdditionalTokusei(TOKUSEI_ENEMY_DAMAGE, dmgStacks);
  }

  for (uint8_t m : instance->GetClockModifiers()) {
    for (int32_t slot : {SLOT_ALL, SLOT_DEMONS, SLOT_ENEMIES}) {
      int32_t tokuseiID = CLOCK_TOKUSEI_BASE + 100 + (int32_t)m * 5 + slot;
      if (definitionManager->GetTokuseiData(tokuseiID)) {
        eState->SetAdditionalTokusei(tokuseiID, 1);
      }
    }
  }
}

bool StephensClock::ApplyToPlayer(
    const std::shared_ptr<ChannelServer>& server,
    const std::shared_ptr<ChannelClientConnection>& client,
    const std::shared_ptr<ZoneInstance>& instance, bool recalc) {
  auto conf = GetConf(server);
  if (!client || !conf) {
    return false;
  }

  auto definitionManager = server->GetDefinitionManager();
  auto state = client->GetClientState();
  auto cState = state->GetCharacterState();
  auto dState = state->GetDemonState();

  // Work out what the character and the partner demon should have
  std::unordered_map<int32_t, uint16_t> both, demonOnly;
  if (IsRun(instance)) {
    bool rewarding = IsRewarding(instance);
    auto v = GetTierValues(instance->GetClockTier(),
                           conf->GetStephensClockDifficultyPercent(),
                           conf->GetStephensClockRewardPercent());
    if (rewarding) {
      both[TOKUSEI_XP] = (uint16_t)((v.XP + 2) / 5);
      both[TOKUSEI_MACCA] = (uint16_t)((v.Macca + 2) / 5);
    }

    for (uint8_t m : instance->GetClockModifiers()) {
      int32_t base = CLOCK_TOKUSEI_BASE + 100 + (int32_t)m * 5;
      both[base + SLOT_ALL] = 1;
      both[base + SLOT_PLAYERS] = 1;
      demonOnly[base + SLOT_DEMONS] = 1;
      if (rewarding) {
        both[base + SLOT_REWARD] = 1;
      }
    }

    for (auto& pair : instance->GetClockBoons()) {
      int32_t base = TOKUSEI_BOON + (int32_t)pair.first * 2;
      both[base] = pair.second;
      if (rewarding) {
        both[base + 1] = pair.second;
      }
    }
  }

  bool changed = false;
  for (int pass = 0; pass < 2; pass++) {
    std::shared_ptr<ActiveEntityState> eState;
    if (pass == 0) {
      eState = cState;
    } else {
      eState = dState;
    }

    if (!eState || (pass == 1 && !dState->GetEntity())) {
      continue;
    }

    auto wanted = both;
    if (pass == 1) {
      for (auto& pair : demonOnly) {
        wanted[pair.first] = pair.second;
      }
    }

    // Drop clock tokusei that no longer apply
    std::list<int32_t> remove;
    for (auto& pair : eState->GetAdditionalTokusei()) {
      if (pair.first >= CLOCK_TOKUSEI_BASE &&
          pair.first < CLOCK_TOKUSEI_BASE + 1000) {
        auto it = wanted.find(pair.first);
        if (it == wanted.end() || !it->second ||
            !definitionManager->GetTokuseiData(pair.first)) {
          remove.push_back(pair.first);
        }
      }
    }

    for (int32_t tokuseiID : remove) {
      eState->RemoveAdditionalTokusei(tokuseiID);
      changed = true;
    }

    for (auto& pair : wanted) {
      if (pair.second && definitionManager->GetTokuseiData(pair.first) &&
          eState->GetAdditionalTokusei(pair.first) != pair.second) {
        eState->SetAdditionalTokusei(pair.first, pair.second);
        changed = true;
      }
    }
  }

  if (changed && recalc) {
    server->GetTokuseiManager()->Recalculate(cState, true);
  }

  return changed;
}

void StephensClock::RefreshPlayers(
    const std::shared_ptr<ChannelServer>& server,
    const std::shared_ptr<ZoneInstance>& instance) {
  for (auto client : instance->GetConnections()) {
    ApplyToPlayer(server, client, instance, true);
  }
}

void StephensClock::Describe(
    const std::shared_ptr<ChannelServer>& server,
    const std::shared_ptr<ChannelClientConnection>& client,
    const std::shared_ptr<ZoneInstance>& instance) {
  auto conf = GetConf(server);
  if (!conf || !IsRun(instance)) {
    return;
  }

  uint8_t tier = instance->GetClockTier();
  auto v = GetTierValues(tier, conf->GetStephensClockDifficultyPercent(),
                         conf->GetStephensClockRewardPercent());
  uint64_t now = ChannelServer::GetServerTime();

  if (instance->GetClockComplete()) {
    Tell(server, client,
         libcomp::String("Stephen's Clock %1: dungeon cleared.")
             .Arg(ROMAN[tier]));
  } else if (instance->GetClockExpired()) {
    Tell(server, client,
         libcomp::String("Stephen's Clock %1 has stopped. Rewards are back "
                         "to normal.")
             .Arg(ROMAN[tier]));
  } else {
    Tell(server, client,
         libcomp::String("Stephen's Clock %1 is ticking: %2 left. A boss "
                         "kill adds %3 min, a death takes %4 min.")
             .Arg(ROMAN[tier])
             .Arg(TimeString(now, instance->GetClockExpire()))
             .Arg(conf->GetStephensClockBossTime() / 60)
             .Arg(conf->GetStephensClockDeathPenalty() / 60));
    Tell(server, client,
         libcomp::String("Rewards: +%1% XP, +%2% Macca and Magnetite, +%3% "
                         "drops, bonus loot on bosses.")
             .Arg(v.XP)
             .Arg(v.Macca)
             .Arg(v.Drops));
  }

  for (uint8_t m : instance->GetClockModifiers()) {
    if (m >= 1 && m <= MODIFIER_COUNT) {
      Tell(server, client,
           libcomp::String("Rule - %1: %2.")
               .Arg(MODIFIERS[m].Name)
               .Arg(MODIFIERS[m].Desc));
    }
  }

  for (auto& pair : instance->GetClockBoons()) {
    if (pair.first >= 1 && pair.first <= BOON_COUNT) {
      Tell(server, client,
           libcomp::String("Boon - %1 x%2: %3.")
               .Arg(BOONS[pair.first].Name)
               .Arg(pair.second)
               .Arg(BOONS[pair.first].Desc));
    }
  }

  auto offer = instance->GetClockBoonOffer();
  if (offer.size() > 0 && IsRewarding(instance)) {
    int32_t idx = 1;
    for (uint8_t b : offer) {
      Tell(server, client,
           libcomp::String("Choose with @boon %1 - %2: %3.")
               .Arg(idx++)
               .Arg(BOONS[b].Name)
               .Arg(BOONS[b].Desc));
    }
  }
}

void StephensClock::ZoneEntered(
    const std::shared_ptr<ChannelServer>& server,
    const std::shared_ptr<ChannelClientConnection>& client,
    const std::shared_ptr<ZoneInstance>& instance) {
  if (!client || !IsRun(instance)) {
    return;
  }

  // Explain the run the first time the player sees it
  auto state = client->GetClientState();
  bool firstZone = state->GetClockSeenInstance() != instance->GetID();
  if (firstZone) {
    state->SetClockSeenInstance(instance->GetID());
    Describe(server, client, instance);
  }

  if (firstZone || !state->GetClockTimerShown()) {
    SendTimer(server, instance, client, true);
  }
}

void StephensClock::InstanceLeft(
    const std::shared_ptr<ChannelServer>& server,
    const std::shared_ptr<ChannelClientConnection>& client,
    const std::shared_ptr<ZoneInstance>& instance) {
  if (client && IsRun(instance)) {
    client->GetClientState()->SetClockSeenInstance(0);
    HideTimer(server, client, true);
  }
}

float StephensClock::GetDropRate(
    const std::shared_ptr<ChannelServer>& server,
    const std::shared_ptr<ZoneInstance>& instance) {
  auto conf = GetConf(server);
  if (!conf || !IsRewarding(instance)) {
    return 1.f;
  }

  auto v = GetTierValues(instance->GetClockTier(), 100,
                         conf->GetStephensClockRewardPercent());
  float rate = 1.f + (float)v.Drops * 0.01f;
  rate += (float)instance->GetClockBoons(BOON_PLUNDER) * 0.15f;

  return rate;
}

std::list<std::shared_ptr<objects::ItemDrop>> StephensClock::GetExtraDrops(
    const std::shared_ptr<ChannelServer>& server,
    const std::shared_ptr<Zone>& zone,
    const std::shared_ptr<ActiveEntityState>& eState) {
  std::list<std::shared_ptr<objects::ItemDrop>> drops;

  auto conf = GetConf(server);
  auto instance = zone ? zone->GetInstance() : nullptr;
  auto eBase = eState ? eState->GetEnemyBase() : nullptr;
  auto spawn = eBase ? eBase->GetSpawnSource() : nullptr;
  if (!conf || !conf->GetStephensClock() || !instance || !IsBoss(spawn)) {
    return drops;
  }

  int32_t level = (int32_t)eState->GetLevel();
  if (IsRewarding(instance)) {
    // Bosses of a clock run carry extra Macca and Magnetite that grows
    // with the tier and the boss level
    auto v = GetTierValues(instance->GetClockTier(), 100,
                           conf->GetStephensClockRewardPercent());
    uint32_t macca = (uint32_t)(40 * level) * (uint32_t)v.Macca / 20;
    uint32_t mag = (uint32_t)(4 * level) * (uint32_t)v.Macca / 20;
    for (auto& pair : std::list<std::pair<uint32_t, uint32_t>>{
             {SVR_CONST.ITEM_MACCA, macca}, {SVR_CONST.ITEM_MAGNETITE, mag}}) {
      if (pair.first && pair.second) {
        uint32_t most = pair.second > 60000 ? 60000 : pair.second;
        auto drop = std::make_shared<objects::ItemDrop>();
        drop->SetItemType(pair.first);
        drop->SetRate(100.f);
        drop->SetMinStack((uint16_t)(most * 3 / 4 > 0 ? most * 3 / 4 : 1));
        drop->SetMaxStack((uint16_t)most);
        drops.push_back(drop);
      }
    }
  } else if (!IsRun(instance)) {
    // Bosses of late game dungeons can drop Stephen's Clock I
    auto variant = instance->GetVariant();
    bool normal =
        !variant ||
        variant->GetInstanceType() ==
            objects::ServerZoneInstanceVariant::InstanceType_t::NORMAL;
    if (normal && level >= (int32_t)conf->GetStephensClockDropLevel() &&
        conf->GetStephensClockDropRate() > 0.f) {
      auto drop = std::make_shared<objects::ItemDrop>();
      drop->SetItemType(conf->GetStephensClockItemID());
      drop->SetRate(conf->GetStephensClockDropRate());
      drops.push_back(drop);
    }
  }

  return drops;
}

void StephensClock::EnemyKilled(
    const std::shared_ptr<ChannelServer>& server,
    const std::shared_ptr<Zone>& zone,
    const std::shared_ptr<ActiveEntityState>& eState) {
  auto conf = GetConf(server);
  auto instance = zone ? zone->GetInstance() : nullptr;
  auto eBase = eState ? eState->GetEnemyBase() : nullptr;
  if (!conf || !IsRun(instance) || !eBase || instance->GetClockComplete()) {
    return;
  }

  if (!IsBoss(eBase->GetSpawnSource())) {
    // Every 20th kill earns a boon, so dungeons with a single boss have
    // them too
    uint16_t kills = (uint16_t)(instance->GetClockKills() + 1);
    instance->SetClockKills(kills);
    if (kills % 20 == 0 && IsRewarding(instance)) {
      OfferBoons(server, instance);
    }

    return;
  }

  instance->SetClockBossKills((uint8_t)(instance->GetClockBossKills() + 1));

  if (IsRewarding(instance)) {
    uint32_t bonus = conf->GetStephensClockBossTime();
    if (bonus) {
      SetExpire(server, instance,
                instance->GetClockExpire() + (uint64_t)bonus * 1000000ULL);
      TellAll(server, instance,
              libcomp::String("Boss defeated: +%1 min. %2 left.")
                  .Arg(bonus / 60)
                  .Arg(TimeString(ChannelServer::GetServerTime(),
                                  instance->GetClockExpire())));
    }
  }

  bool finalZone =
      zone->GetDefinitionID() == instance->GetClockFinalZoneID() &&
      zone->GetDynamicMapID() == instance->GetClockFinalDynamicMapID();
  if (finalZone) {
    // The dungeon is cleared once no boss is left in the final boss room.
    // Check a little later so bosses with several forms can respawn first.
    uint32_t instanceID = instance->GetID();
    uint32_t zoneID = zone->GetDefinitionID();
    uint32_t dynamicMapID = zone->GetDynamicMapID();
    std::weak_ptr<ChannelServer> weak = server;
    server->GetTimerManager()->ScheduleEventIn(
        6, [weak, instanceID, zoneID, dynamicMapID]() {
          auto pServer = weak.lock();
          auto pInstance =
              pServer ? pServer->GetZoneManager()->GetInstance(instanceID)
                      : nullptr;
          auto pZone =
              pInstance ? pInstance->GetZone(zoneID, dynamicMapID) : nullptr;
          if (!pZone || pInstance->GetClockComplete()) {
            return;
          }

          for (auto enemy : pZone->GetEnemies()) {
            auto base = enemy->GetEnemyBase();
            if (enemy->IsAlive() && base && IsBoss(base->GetSpawnSource())) {
              return;
            }
          }

          StephensClock::Complete(pServer, pInstance);
        });
  } else if (IsRewarding(instance)) {
    OfferBoons(server, instance);
  }
}

void StephensClock::OfferBoons(const std::shared_ptr<ChannelServer>& server,
                               const std::shared_ptr<ZoneInstance>& instance) {
  // An offer nobody answered is settled with its first choice
  auto old = instance->GetClockBoonOffer();
  if (old.size() > 0) {
    TakeBoon(server, instance, old.front());
  }

  std::set<uint8_t> offer;
  while (offer.size() < 3) {
    offer.insert((uint8_t)RNG(uint16_t, 1, (uint16_t)BOON_COUNT));
  }

  instance->ClearClockBoonOffer();
  for (uint8_t b : offer) {
    instance->AppendClockBoonOffer(b);
  }

  TellAll(server, instance, "The clock offers a boon for the rest of the run:");

  int32_t idx = 1;
  for (uint8_t b : offer) {
    TellAll(server, instance,
            libcomp::String("@boon %1 - %2: %3.")
                .Arg(idx++)
                .Arg(BOONS[b].Name)
                .Arg(BOONS[b].Desc));
  }
}

void StephensClock::TakeBoon(const std::shared_ptr<ChannelServer>& server,
                             const std::shared_ptr<ZoneInstance>& instance,
                             uint8_t boon) {
  instance->ClearClockBoonOffer();
  if (boon < 1 || boon > BOON_COUNT) {
    return;
  }

  uint8_t stacks = (uint8_t)(instance->GetClockBoons(boon) + 1);
  instance->SetClockBoons(boon, stacks);

  TellAll(server, instance,
          libcomp::String("Boon gained - %1: %2.")
              .Arg(BOONS[boon].Name)
              .Arg(BOONS[boon].Desc));

  if (boon == BOON_TIME) {
    if (IsRewarding(instance)) {
      SetExpire(server, instance,
                instance->GetClockExpire() + 300ULL * 1000000ULL);
    }
  } else {
    RefreshPlayers(server, instance);
  }
}

void StephensClock::PlayersKilled(const std::shared_ptr<ChannelServer>& server,
                                  const std::shared_ptr<ZoneInstance>& instance,
                                  size_t count) {
  auto conf = GetConf(server);
  if (!conf || !count || !IsRewarding(instance) ||
      instance->GetClockComplete()) {
    return;
  }

  uint64_t penalty = (uint64_t)conf->GetStephensClockDeathPenalty() *
                     (uint64_t)count * 1000000ULL;
  if (!penalty) {
    return;
  }

  uint64_t now = ChannelServer::GetServerTime();
  uint64_t expire = instance->GetClockExpire();
  expire = expire > penalty ? expire - penalty : 0;

  if (expire <= now) {
    Expire(server, instance);
  } else {
    SetExpire(server, instance, expire);
    TellAll(server, instance,
            libcomp::String("A death costs %1 min. %2 left.")
                .Arg((uint32_t)(conf->GetStephensClockDeathPenalty() * count / 60))
                .Arg(TimeString(now, expire)));
  }
}

void StephensClock::SetExpire(const std::shared_ptr<ChannelServer>& server,
                              const std::shared_ptr<ZoneInstance>& instance,
                              uint64_t expire) {
  auto conf = GetConf(server);
  if (!conf) {
    return;
  }

  // The client counts down from the length of its TimeLimitData entry, so
  // the clock can never show more than that
  uint64_t now = ChannelServer::GetServerTime();
  uint64_t latest =
      now + (uint64_t)conf->GetStephensClockTimerLength() * 1000000ULL;
  if (expire > latest) {
    expire = latest;
  }

  instance->SetClockExpire(expire);

  int scheduleIn = expire > now ? (int)((expire - now) / 1000000ULL) + 1 : 0;
  uint32_t instanceID = instance->GetID();
  std::weak_ptr<ChannelServer> weak = server;
  server->GetTimerManager()->ScheduleEventIn(
      scheduleIn, [weak, instanceID, expire]() {
        auto pServer = weak.lock();
        auto pInstance =
            pServer ? pServer->GetZoneManager()->GetInstance(instanceID)
                    : nullptr;
        if (pInstance && pInstance->GetClockExpire() == expire &&
            StephensClock::IsRewarding(pInstance) &&
            !pInstance->GetClockComplete()) {
          StephensClock::Expire(pServer, pInstance);
        }
      });

  if (instance->GetAccessed()) {
    SendTimer(server, instance, nullptr, false);
  }
}

void StephensClock::Expire(const std::shared_ptr<ChannelServer>& server,
                           const std::shared_ptr<ZoneInstance>& instance) {
  if (!IsRewarding(instance)) {
    return;
  }

  instance->SetClockExpired(true);
  instance->ClearClockBoonOffer();

  for (auto client : instance->GetConnections()) {
    HideTimer(server, client, false);
    ApplyToPlayer(server, client, instance, true);
  }

  TellAll(server, instance,
          "Stephen's Clock has stopped. You can still finish the dungeon, "
          "but its rewards are back to normal.");
}

void StephensClock::Complete(const std::shared_ptr<ChannelServer>& server,
                             const std::shared_ptr<ZoneInstance>& instance) {
  auto conf = GetConf(server);
  if (!conf || !IsRun(instance) || instance->GetClockComplete()) {
    return;
  }

  instance->SetClockComplete(true);
  instance->ClearClockBoonOffer();

  if (instance->GetClockExpired()) {
    TellAll(server, instance,
            "Dungeon cleared, but Stephen's Clock had already stopped.");
    return;
  }

  // Stop the countdown; the rewards stay until everyone has left
  uint64_t now = ChannelServer::GetServerTime();
  libcomp::String left = TimeString(now, instance->GetClockExpire());
  instance->SetClockExpire(0);
  for (auto client : instance->GetConnections()) {
    HideTimer(server, client, false);
  }

  uint8_t tier = instance->GetClockTier();
  uint8_t next = (uint8_t)(tier < CLOCK_MAX_TIER ? tier + 1 : CLOCK_MAX_TIER);

  TellAll(server, instance,
          libcomp::String("Dungeon cleared with %1 left on Stephen's Clock "
                          "%2!")
              .Arg(left)
              .Arg(ROMAN[tier]));

  // Only the player who used the clock gets the next one
  auto owner = server->GetManagerConnection()->GetEntityClient(
      instance->GetClockOwnerCID(), true);
  if (owner) {
    std::unordered_map<uint32_t, uint32_t> reward;
    reward[conf->GetStephensClockItemID() + (uint32_t)(next - 1)] = 1;
    if (server->GetCharacterManager()->AddRemoveItems(owner, reward, true)) {
      Tell(server, owner,
           libcomp::String("You receive Stephen's Clock %1.").Arg(ROMAN[next]));
    } else {
      // No room: kept on the instance until the player asks with @clock
      Tell(server, owner,
           libcomp::String("Your inventory is full! Make room and type "
                           "@clock to receive Stephen's Clock %1 before you "
                           "leave.")
               .Arg(ROMAN[next]));
      instance->SetClockRewardPending(next);
    }
  }
}

void StephensClock::SendTimer(
    const std::shared_ptr<ChannelServer>& server,
    const std::shared_ptr<ZoneInstance>& instance,
    const std::shared_ptr<ChannelClientConnection>& client, bool queue) {
  auto conf = GetConf(server);
  if (!conf || !IsRewarding(instance) || !instance->GetClockExpire() ||
      instance->GetClockComplete()) {
    return;
  }

  // A dungeon's own timer uses the same display and comes first
  if (instance->GetTimeLimitData() && instance->GetTimerStart() &&
      !instance->GetTimerStop()) {
    return;
  }

  // The client shows (length - time since start), so report the start
  // that leaves the time we want
  uint64_t length =
      (uint64_t)conf->GetStephensClockTimerLength() * 1000000ULL;
  uint64_t expire = instance->GetClockExpire();
  uint64_t start = expire > length ? expire - length : 1;

  libcomp::Packet p;
  p.WritePacketCode(ChannelToClientPacketCode_t::PACKET_TIME_LIMIT_UPDATE);
  p.WriteS8((int8_t)conf->GetStephensClockTimerID());

  RelativeTimeMap timeMap;
  timeMap[p.Size()] = start;
  p.WriteFloat(0.f);

  p.WriteU8(1);
  p.WriteU8(0);

  std::list<std::shared_ptr<ChannelClientConnection>> connections;
  if (client) {
    connections.push_back(client);
  } else {
    connections = instance->GetConnections();
  }

  ChannelClientConnection::SendRelativeTimePacket(connections, p, timeMap,
                                                  queue);

  for (auto c : connections) {
    c->GetClientState()->SetClockTimerShown(true);
  }
}

void StephensClock::HideTimer(
    const std::shared_ptr<ChannelServer>& server,
    const std::shared_ptr<ChannelClientConnection>& client, bool queue) {
  auto conf = GetConf(server);
  if (!conf || !client || !client->GetClientState()->GetClockTimerShown()) {
    return;
  }

  client->GetClientState()->SetClockTimerShown(false);

  libcomp::Packet p;
  p.WritePacketCode(ChannelToClientPacketCode_t::PACKET_TIME_LIMIT_END);
  p.WriteU32Little((uint32_t)conf->GetStephensClockTimerID());
  p.WriteS8(0);
  p.WriteU8(1);

  if (queue) {
    client->QueuePacket(p);
  } else {
    client->SendPacket(p);
  }
}

void StephensClock::Command(
    const std::shared_ptr<ChannelServer>& server,
    const std::shared_ptr<ChannelClientConnection>& client, bool boon,
    int32_t choice) {
  auto conf = GetConf(server);
  if (!conf || !client) {
    return;
  }

  if (!conf->GetStephensClock()) {
    Tell(server, client, "Stephen's Clock is turned off on this server.");
    return;
  }

  auto state = client->GetClientState();
  auto zone = state->GetZone();
  auto instance = zone ? zone->GetInstance() : nullptr;

  if (!IsRun(instance)) {
    uint8_t tier = GetItemTier(server, state->GetClockArmedItem());
    if (tier) {
      Tell(server, client,
           libcomp::String("Stephen's Clock %1 is wound. It is used up when "
                           "you enter the next dungeon you open.")
               .Arg(ROMAN[tier]));
    } else {
      Tell(server, client,
           "No clock is wound. Use a Stephen's Clock, then open a dungeon. "
           "Bosses of high level dungeons drop Stephen's Clock I.");
    }

    return;
  }

  // A reward that did not fit earlier
  if (instance->GetClockComplete() && instance->GetClockRewardPending() &&
      state->GetWorldCID() == instance->GetClockOwnerCID()) {
    uint8_t next = instance->GetClockRewardPending();
    std::unordered_map<uint32_t, uint32_t> reward;
    reward[conf->GetStephensClockItemID() + (uint32_t)(next - 1)] = 1;
    if (server->GetCharacterManager()->AddRemoveItems(client, reward, true)) {
      Tell(server, client,
           libcomp::String("You receive Stephen's Clock %1.")
               .Arg(ROMAN[next]));
      instance->SetClockRewardPending(0);
    } else {
      Tell(server, client, "Your inventory is still full.");
    }

    return;
  }

  if (boon) {
    auto offer = instance->GetClockBoonOffer();
    if (!IsRewarding(instance) || offer.size() == 0) {
      Tell(server, client, "There is no boon to choose right now.");
    } else if (choice < 1 || choice > (int32_t)offer.size()) {
      Tell(server, client,
           libcomp::String("Type @boon 1 to @boon %1.")
               .Arg((uint32_t)offer.size()));
    } else {
      auto it = offer.begin();
      std::advance(it, choice - 1);
      TakeBoon(server, instance, *it);
    }

    return;
  }

  Describe(server, client, instance);
}
