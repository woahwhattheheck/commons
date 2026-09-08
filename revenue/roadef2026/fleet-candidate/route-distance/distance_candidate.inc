    int distance(int d, const Route& a, const Route& b) const {
        if (a == b) return 0;
        // At most eight segments fit in fixed local storage. Retain unique
        // directed-segment semantics, including repeated/degenerate waypoints.
        // Longer caller routes use the original general-length implementation.
        if (a.size() <= 7 && b.size() <= 7) {
            using Segment = std::pair<int, int>;
            Segment x[8], y[8];
            auto collect = [&](const Route& path, Segment* out) {
                int count = 0;
                int from = demands[d].from;
                auto append = [&](int to) {
                    Segment value{from, to};
                    int j = 0;
                    while (j < count && out[j] != value) ++j;
                    if (j == count) out[count++] = value;
                    from = to;
                };
                for (int to : path) append(to);
                append(demands[d].to);
                return count;
            };
            int nx = collect(a, x), ny = collect(b, y), common = 0;
            for (int i = 0; i < nx; ++i) {
                int j = 0;
                while (j < ny && x[i] != y[j]) ++j;
                common += static_cast<int>(j < ny);
            }
            return nx + ny - 2 * common;
        }
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
