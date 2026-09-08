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
