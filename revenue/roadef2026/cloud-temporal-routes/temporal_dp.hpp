// SPDX-License-Identifier: MIT
// Exact lexicographic route-menu optimization across bounded time layers.
#pragma once
#include <algorithm>
#include <cstddef>
#include <functional>
#include <iterator>
#include <limits>
#include <stdexcept>
#include <utility>
#include <vector>

namespace dock_temporal {
using Objective = std::vector<long long>;
struct Option {
    bool reachable = true;
    Objective cost; // All edge saturations at this slot, descending, six-decimal integers.
};
struct Result {
    bool complete = false;
    bool feasible = false;
    std::vector<int> choices;
    Objective objective;
    std::size_t transitions_examined = 0;
};

// Unchanged loads cancel in multiset lex order. More generally, if X < Y,
// sorted(X union Z) < sorted(Y union Z). Thus for the same terminal option,
// only the best feasible prefix must be retained; adding that option's cost
// cannot reverse the prefix order. No sum/peak surrogate is used.
//
// transition_cost(t, previous, current) is a nonnegative integer. budgets[t]
// is the residual budget with all OTHER demands fixed; budgets[0] is ignored.
// Cancellation returns incomplete, never a partial schedule to execute.
// Valid inputs and callback behavior are a caller contract; malformed matrices
// and negative transition costs are rejected before they can choose a route.
template<class Distance, class Cancel>
Result solve(const std::vector<std::vector<Option>>& layers,
             const std::vector<int>& budgets, Distance transition_cost, Cancel cancel) {
    Result result;
    const std::size_t h = layers.size();
    if (h == 0 || budgets.size() != h) throw std::invalid_argument("invalid temporal horizon");
    std::size_t width = 0;
    bool have_width = false;
    for (std::size_t t = 0; t < h; ++t) {
        if (cancel()) return result;
        if (layers[t].empty()) throw std::invalid_argument("empty route menu");
        if (t && budgets[t] < 0) throw std::invalid_argument("negative residual budget");
        for (const auto& option : layers[t]) {
            if (!option.reachable) continue;
            if (!have_width) { width = option.cost.size(); have_width = true; }
            if (option.cost.size() != width ||
                !std::is_sorted(option.cost.begin(), option.cost.end(), std::greater<long long>()))
                throw std::invalid_argument("unaligned or unsorted objective");
            if (!option.cost.empty() && option.cost.back() < 0)
                throw std::invalid_argument("negative load coordinate");
        }
    }
    if (have_width && h > std::numeric_limits<std::size_t>::max() / std::max<std::size_t>(width, 1))
        throw std::length_error("temporal objective size overflow");
    std::vector<Objective> previous(layers[0].size());
    std::vector<bool> previous_ok(layers[0].size(), false);
    std::vector<std::vector<int>> parents(h);
    parents[0].assign(layers[0].size(), -1);
    for (std::size_t k = 0; k < layers[0].size(); ++k) {
        if (cancel()) return result;
        if (layers[0][k].reachable) {
            previous[k] = layers[0][k].cost;
            previous_ok[k] = true;
        }
    }
    for (std::size_t t = 1; t < h; ++t) {
        std::vector<Objective> current(layers[t].size());
        std::vector<bool> current_ok(layers[t].size(), false);
        parents[t].assign(layers[t].size(), -1);
        for (std::size_t k = 0; k < layers[t].size(); ++k) {
            if (cancel()) return result;
            if (!layers[t][k].reachable) continue;
            int best = -1;
            for (std::size_t j = 0; j < previous.size(); ++j) {
                if (cancel()) return result;
                if (!previous_ok[j]) continue;
                int used = transition_cost(t, j, k);
                ++result.transitions_examined;
                if (used < 0) throw std::invalid_argument("negative transition cost");
                if (used > budgets[t]) continue;
                if (best < 0 || previous[j] < previous[static_cast<std::size_t>(best)])
                    best = static_cast<int>(j);
            }
            if (best < 0) continue;
            const auto& prefix = previous[static_cast<std::size_t>(best)];
            const auto& local = layers[t][k].cost;
            current[k].reserve(prefix.size() + local.size());
            std::merge(prefix.begin(), prefix.end(), local.begin(), local.end(),
                       std::back_inserter(current[k]), std::greater<long long>());
            parents[t][k] = best;
            current_ok[k] = true;
        }
        previous.swap(current); previous_ok.swap(current_ok);
    }
    if (cancel()) return result;
    int best = -1;
    for (std::size_t k = 0; k < previous.size(); ++k)
        if (previous_ok[k] && (best < 0 || previous[k] < previous[static_cast<std::size_t>(best)]))
            best = static_cast<int>(k);
    result.complete = true;
    if (best < 0) return result;
    result.feasible = true;
    result.objective = std::move(previous[static_cast<std::size_t>(best)]);
    result.choices.resize(h);
    for (std::size_t t = h; t-- > 0;) {
        result.choices[t] = best;
        best = parents[t][static_cast<std::size_t>(best)];
    }
    return result;
}
} // namespace dock_temporal
