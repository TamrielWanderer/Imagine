/**
 * @file server/channel/src/StephensClock.h
 * @ingroup channel
 *
 * @brief Stephen's Clock: rogue-like dungeon runs.
 *
 * A player winds a Stephen's Clock item (tier I to X). The next dungeon
 * instance they create becomes a "clock run": enemies are scaled to the
 * party and the tier, random modifiers are rolled, a countdown runs, and
 * rewards are better until the countdown ends. See docs/stephens-clock.md.
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

#ifndef SERVER_CHANNEL_SRC_STEPHENSCLOCK_H
#define SERVER_CHANNEL_SRC_STEPHENSCLOCK_H

// libcomp Includes
#include <CString.h>

// Standard C++11 Includes
#include <list>
#include <memory>

namespace objects {
class ItemDrop;
class Spawn;
}  // namespace objects

namespace channel {

class ActiveEntityState;
class ChannelClientConnection;
class ChannelServer;
class Zone;
class ZoneInstance;

/// First tokusei ID used by the clock (datastore/data/tokusei/
/// tokusei_stephens_clock.xml). Everything up to +999 belongs to it.
const int32_t CLOCK_TOKUSEI_BASE = 9100000;

/// Highest clock tier
const uint8_t CLOCK_MAX_TIER = 10;

/**
 * Numbers that decide how hard and how rewarding a tier is. Kept in one
 * place so the balance can be read (and tested) on its own.
 */
struct ClockTierValues {
  /// Enemy level floor relative to the highest level in the party
  int8_t LevelOffset;
  /// Enemy max HP bonus in percent (before the party size bonus)
  uint16_t EnemyHP;
  /// Enemy damage bonus in percent
  uint16_t EnemyDamage;
  /// XP bonus in percent
  uint16_t XP;
  /// Macca and magnetite bonus in percent
  uint16_t Macca;
  /// Drop rate bonus in percent
  uint16_t Drops;
  /// Number of random modifiers
  uint8_t Modifiers;
};

/**
 * Static helpers that implement Stephen's Clock. All state lives on the
 * zone instance (ZoneInstanceObject Clock* members) and the client state.
 */
class StephensClock {
 public:
  /**
   * Get the balance numbers of a tier.
   * @param tier Tier from 1 to 10
   * @param difficulty Difficulty scale in percent
   * @param reward Reward scale in percent
   */
  static ClockTierValues GetTierValues(uint8_t tier, uint16_t difficulty = 100,
                                       uint16_t reward = 100);

  /**
   * Get the tier of a clock item.
   * @return 1 to 10 or 0 if the item is not a clock (or the system is off)
   */
  static uint8_t GetItemTier(const std::shared_ptr<ChannelServer>& server,
                             uint32_t itemID);

  /// Wind or unwind the clock when its item is used
  static void UseItem(const std::shared_ptr<ChannelServer>& server,
                      const std::shared_ptr<ChannelClientConnection>& client,
                      uint32_t itemID);

  /// Called when a player created an instance on this channel
  static void InstanceCreated(
      const std::shared_ptr<ChannelServer>& server,
      const std::shared_ptr<ChannelClientConnection>& client,
      const std::shared_ptr<ZoneInstance>& instance);

  /// Called before a player is moved into an instance: starts a pending run
  static void InstanceEntering(const std::shared_ptr<ChannelServer>& server,
                               const std::shared_ptr<ZoneInstance>& instance);

  /// true if the instance is a clock run (expired or not)
  static bool IsRun(const std::shared_ptr<ZoneInstance>& instance);

  /// true if the instance is a clock run whose rewards still apply
  static bool IsRewarding(const std::shared_ptr<ZoneInstance>& instance);

  /// Level an enemy spawns with in the zone
  static int8_t GetEnemyLevel(const std::shared_ptr<Zone>& zone,
                              const std::shared_ptr<objects::Spawn>& spawn,
                              bool asAlly, int8_t level);

  /// Set the clock effects on a new enemy (before its stats are calculated)
  static void ApplyToEnemy(const std::shared_ptr<ChannelServer>& server,
                           const std::shared_ptr<Zone>& zone,
                           const std::shared_ptr<ActiveEntityState>& eState,
                           const std::shared_ptr<objects::Spawn>& spawn,
                           bool asAlly);

  /**
   * Set (or clear) the clock effects on a player and their partner demon.
   * @param recalc Recalculate tokusei and stats afterwards
   * @return true if anything changed
   */
  static bool ApplyToPlayer(
      const std::shared_ptr<ChannelServer>& server,
      const std::shared_ptr<ChannelClientConnection>& client,
      const std::shared_ptr<ZoneInstance>& instance, bool recalc);

  /// Called when a player finished entering a zone of an instance
  static void ZoneEntered(const std::shared_ptr<ChannelServer>& server,
                          const std::shared_ptr<ChannelClientConnection>& client,
                          const std::shared_ptr<ZoneInstance>& instance);

  /// Called when a player leaves an instance
  static void InstanceLeft(const std::shared_ptr<ChannelServer>& server,
                           const std::shared_ptr<ChannelClientConnection>& client,
                           const std::shared_ptr<ZoneInstance>& instance);

  /// Drop rate multiplier of the instance (1 outside of clock runs)
  static float GetDropRate(const std::shared_ptr<ChannelServer>& server,
                           const std::shared_ptr<ZoneInstance>& instance);

  /// Extra drops for a killed enemy (clock bonus, or Stephen's Clock I)
  static std::list<std::shared_ptr<objects::ItemDrop>> GetExtraDrops(
      const std::shared_ptr<ChannelServer>& server,
      const std::shared_ptr<Zone>& zone,
      const std::shared_ptr<ActiveEntityState>& eState);

  /// Called for every enemy killed in an instance
  static void EnemyKilled(const std::shared_ptr<ChannelServer>& server,
                          const std::shared_ptr<Zone>& zone,
                          const std::shared_ptr<ActiveEntityState>& eState);

  /// Called when player characters died in an instance
  static void PlayersKilled(const std::shared_ptr<ChannelServer>& server,
                            const std::shared_ptr<ZoneInstance>& instance,
                            size_t count);

  /// Show or refresh the countdown (client null = everyone in the instance)
  static void SendTimer(const std::shared_ptr<ChannelServer>& server,
                        const std::shared_ptr<ZoneInstance>& instance,
                        const std::shared_ptr<ChannelClientConnection>& client,
                        bool queue);

  /// Hide the countdown for one client
  /// (success shows the client's CLEAR message, otherwise its failure one)
  static void HideTimer(const std::shared_ptr<ChannelServer>& server,
                        const std::shared_ptr<ChannelClientConnection>& client,
                        bool queue, bool success = false);

  /// "@clock" and "@boon N" chat commands
  static void Command(const std::shared_ptr<ChannelServer>& server,
                      const std::shared_ptr<ChannelClientConnection>& client,
                      bool boon, int32_t choice);

 private:
  static void Tell(const std::shared_ptr<ChannelServer>& server,
                   const std::shared_ptr<ChannelClientConnection>& client,
                   const libcomp::String& message);
  static void TellAll(const std::shared_ptr<ChannelServer>& server,
                      const std::shared_ptr<ZoneInstance>& instance,
                      const libcomp::String& message);
  static void Describe(const std::shared_ptr<ChannelServer>& server,
                       const std::shared_ptr<ChannelClientConnection>& client,
                       const std::shared_ptr<ZoneInstance>& instance);
  static void SetExpire(const std::shared_ptr<ChannelServer>& server,
                        const std::shared_ptr<ZoneInstance>& instance,
                        uint64_t expire);
  static void Expire(const std::shared_ptr<ChannelServer>& server,
                     const std::shared_ptr<ZoneInstance>& instance);
  static void Complete(const std::shared_ptr<ChannelServer>& server,
                       const std::shared_ptr<ZoneInstance>& instance);
  static void OfferBoons(const std::shared_ptr<ChannelServer>& server,
                         const std::shared_ptr<ZoneInstance>& instance);
  static void TakeBoon(const std::shared_ptr<ChannelServer>& server,
                       const std::shared_ptr<ZoneInstance>& instance,
                       uint8_t boon);
  static void RefreshPlayers(const std::shared_ptr<ChannelServer>& server,
                             const std::shared_ptr<ZoneInstance>& instance);
};

}  // namespace channel

#endif  // SERVER_CHANNEL_SRC_STEPHENSCLOCK_H
