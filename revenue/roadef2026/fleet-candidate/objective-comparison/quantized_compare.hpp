// SPDX-License-Identifier: MIT
// Exact optimization of the existing descending, quantized load-vector comparison.
#pragma once
#include <algorithm>
#include <cstddef>
#include <functional>
#include <limits>
#include <vector>

namespace delve {
struct CompareStats { unsigned long long maxima = 0, counts = 0, fallback = 0; };

// The input vectors may be reordered. Their contents are not otherwise changed.
// This returns precisely sort(after, greater) < sort(before, greater), including
// unequal-length inputs. Solver moveTogether supplies equal-length vectors.
inline bool quantized_improves(std::vector<long long>& before,
                               std::vector<long long>& after,
                               CompareStats* stats = nullptr) {
    if (before.size() == after.size() && !before.empty()) {
        long long bmax = before.front(), amax = after.front();
        std::size_t bcount = 0, acount = 0;
        for (std::size_t i = 0; i < before.size(); ++i) {
            const auto b = before[i], a = after[i];
            if (b > bmax) { bmax = b; bcount = 1; }
            else if (b == bmax) { ++bcount; }
            if (a > amax) { amax = a; acount = 1; }
            else if (a == amax) { ++acount; }
        }
        if (amax != bmax) {
            if (stats) ++stats->maxima;
            return amax < bmax;
        }
        if (acount != bcount) {
            if (stats) ++stats->counts;
            return acount < bcount;
        }
    }
    if (stats) ++stats->fallback;
    std::sort(before.begin(), before.end(), std::greater<long long>());
    std::sort(after.begin(), after.end(), std::greater<long long>());
    return after < before;
}
} // namespace delve
