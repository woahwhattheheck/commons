    int distance(int d, const Route& a, const Route& b) const {
        if (a == b) return 0;
        auto segments = [&](const Route& path) {
            std::set<std::pair<int, int>> result;
            int from = demands[d].from;
            for (int to : path) { result.emplace(from, to); from = to; }
            result.emplace(from, demands[d].to);
            return result;
        };
        auto x = segments(a), y = segments(b);
        int common = 0;
        for (auto item : x) common += static_cast<int>(y.count(item));
        return static_cast<int>(x.size() + y.size()) - 2 * common;
    }
