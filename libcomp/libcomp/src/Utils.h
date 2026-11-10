/**
 * @file libcomp/src/Utils.h
 * @ingroup libcomp
 *
 * @author COMP Omega <compomega@tutanota.com>
 *
 * @brief Platform specific utility functions.
 *
 * This file is part of the COMP_hack Library (libcomp).
 *
 * Copyright (C) 2012-2021 COMP_hack Team <compomega@tutanota.com>
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

#ifndef LIBCOMP_SRC_UTILS_H
#define LIBCOMP_SRC_UTILS_H

// Standard C Includes
#include <cstdlib>
#include <set>

/**
 * Get the size of an array.
 * @param arr Array to get the size of.
 * @returns Size of the array.
 */
template <typename T, size_t N>
static constexpr size_t countof(T const (&arr)[N]) {
  // https://stackoverflow.com/a/874276
  (void)arr;

  return N;
}

/**
 * Compute the differences between two sets and return
 * the unique entries in each set.
 * @param a The first set
 * @param b The second set
 * @param only_in_a Set containing elements that are only in the first set
 * @param only_in_b Set containing elements that are only in the second set
 */
template <typename T>
void set_diff(const std::set<T> &a, const std::set<T> &b,
              std::set<T> &only_in_a, std::set<T> &only_in_b) {
  auto it_a = a.begin();
  auto it_b = b.begin();

  while (it_a != a.end() || it_b != b.end()) {
    if (it_b == b.end()) {
      only_in_a.insert(*it_a++);
    } else if (it_a == a.end()) {
      only_in_b.insert(*it_b++);
    } else if (*it_a == *it_b) {
      it_a++;
      it_b++;
    } else if (*it_a < *it_b) {
      only_in_a.insert(*it_a++);
    } else {
      only_in_b.insert(*it_b++);
    }
  }
}

#endif  // LIBCOMP_SRC_UTILS_H
