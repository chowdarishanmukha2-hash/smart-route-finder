"""
Route Engine - compares multiple paths, finds the cheapest, explains why.
Run:  python route_engine.py                      (interactive)
      python route_engine.py Hyderabad Chennai    (direct)
Options: --fuel 8  --time-value 200  --toll 1  --k 4
No external libraries needed (Python 3.8+).
"""
import argparse
import heapq

# ---------------- DATA: edit freely ----------------
# (city_a, city_b, distance_km, minutes, toll_rupees)
ROADS = [
    ("Hyderabad", "Warangal", 150, 165, 120),
    ("Hyderabad", "Vijayawada", 270, 270, 290),
    ("Hyderabad", "Nagpur", 500, 480, 450),
    ("Hyderabad", "Kurnool", 215, 195, 180),
    ("Hyderabad", "Bengaluru", 570, 530, 520),
    ("Warangal", "Vijayawada", 235, 250, 150),
    ("Warangal", "Visakhapatnam", 430, 460, 300),
    ("Warangal", "Nagpur", 330, 360, 200),
    ("Vijayawada", "Visakhapatnam", 350, 360, 260),
    ("Vijayawada", "Chennai", 450, 450, 380),
    ("Vijayawada", "Tirupati", 390, 400, 250),
    ("Kurnool", "Bengaluru", 360, 390, 250),
    ("Kurnool", "Tirupati", 340, 380, 150),
    ("Bengaluru", "Chennai", 345, 330, 270),
    ("Bengaluru", "Tirupati", 250, 260, 100),
    ("Tirupati", "Chennai", 135, 150, 80),
]


class RouteEngine:
    def __init__(self, roads, fuel_per_km=8, time_value_per_hr=200, toll_weight=1.0):
        self.fuel, self.tv, self.tw = fuel_per_km, time_value_per_hr, toll_weight
        self.graph, self.edges = {}, {}
        for a, b, km, mins, toll in roads:
            self.edges[frozenset((a, b))] = (km, mins, toll)
            self.graph.setdefault(a, []).append(b)
            self.graph.setdefault(b, []).append(a)

    # ---- cost model: fuel + value of time + tolls, all in rupees ----
    def edge_parts(self, a, b):
        km, mins, toll = self.edges[frozenset((a, b))]
        return {"fuel": km * self.fuel, "time": mins / 60 * self.tv,
                "toll": toll * self.tw, "km": km, "min": mins, "raw_toll": toll}

    def edge_cost(self, a, b):
        p = self.edge_parts(a, b)
        return p["fuel"] + p["time"] + p["toll"]

    def stats(self, path):
        s = dict(fuel=0, time=0, toll=0, km=0, min=0, raw_toll=0)
        for a, b in zip(path, path[1:]):
            for k, v in self.edge_parts(a, b).items():
                s[k] += v
        s["total"] = s["fuel"] + s["time"] + s["toll"]
        s["path"] = path
        return s

    # ---- Dijkstra (banned nodes/edges let Yen reuse it) ----
    def dijkstra(self, src, dst, banned_nodes=frozenset(), banned_edges=frozenset()):
        dist, prev, pq = {src: 0}, {}, [(0, src)]
        while pq:
            d, u = heapq.heappop(pq)
            if u == dst:
                path = [dst]
                while path[-1] != src:
                    path.append(prev[path[-1]])
                return path[::-1]
            if d > dist.get(u, float("inf")):
                continue
            for v in self.graph[u]:
                if v in banned_nodes or frozenset((u, v)) in banned_edges:
                    continue
                nd = d + self.edge_cost(u, v)
                if nd < dist.get(v, float("inf")):
                    dist[v], prev[v] = nd, u
                    heapq.heappush(pq, (nd, v))
        return None

    # ---- Yen's algorithm: K cheapest loop-free routes ----
    def k_routes(self, src, dst, k=4):
        first = self.dijkstra(src, dst)
        if not first:
            return []
        found, candidates = [first], []
        for _ in range(1, k):
            last = found[-1]
            for i in range(len(last) - 1):
                root = last[: i + 1]
                banned_edges = {frozenset((p[i], p[i + 1])) for p in found
                                if len(p) > i + 1 and p[: i + 1] == root}
                spur = self.dijkstra(last[i], dst, frozenset(root[:-1]), banned_edges)
                if spur:
                    cand = root[:-1] + spur
                    if cand not in found and cand not in candidates:
                        candidates.append(cand)
            if not candidates:
                break
            candidates.sort(key=lambda p: self.stats(p)["total"])
            found.append(candidates.pop(0))
        return [self.stats(p) for p in found]


# ---------------- presentation ----------------
def hm(m):
    return f"{int(m // 60)}h {int(round(m % 60)):02d}m"


def inr(x):
    return f"Rs {x:,.0f}"


def report(routes):
    best = routes[0]
    print("\nROUTES RANKED BY TOTAL COST")
    print("-" * 70)
    for i, r in enumerate(routes):
        tag = "  <-- OPTIMAL" if i == 0 else f"  (+{inr(r['total'] - best['total'])})"
        print(f"{i + 1}. {' -> '.join(r['path'])}{tag}")
        print(f"   {r['km']} km | {hm(r['min'])} | tolls {inr(r['raw_toll'])} | "
              f"fuel {inr(r['fuel'])} + time {inr(r['time'])} + tolls {inr(r['toll'])} "
              f"= {inr(r['total'])}")

    fastest = min(routes, key=lambda r: r["min"])
    shortest = min(routes, key=lambda r: r["km"])
    print("\nWHY THIS ROUTE?")
    print("-" * 70)
    print(f"* Lowest combined cost among {len(routes)} routes: {inr(best['total'])}.")
    if fastest is best:
        print("* It is also the fastest route - no trade-off needed.")
    else:
        print(f"* Not the fastest: {' -> '.join(fastest['path'])} saves "
              f"{hm(best['min'] - fastest['min'])} but costs "
              f"{inr(fastest['total'] - best['total'])} more.")
    if shortest is best:
        print("* It is also the shortest by distance.")
    else:
        print(f"* Not the shortest: {' -> '.join(shortest['path'])} is "
              f"{best['km'] - shortest['km']} km shorter but loses on cost overall.")
    if len(routes) > 1:
        o = routes[1]
        diffs = {k: o[k] - best[k] for k in ("fuel", "time", "toll")}
        main = max(diffs, key=lambda k: abs(diffs[k]))
        print(f"* Runner-up costs {inr(o['total'] - best['total'])} more "
              f"({(o['total'] / best['total'] - 1) * 100:.1f}%); biggest driver: {main}.")
    print("* Guarantee: costs are non-negative, so Dijkstra's result is the true minimum.")


def pick(prompt, cities):
    print(f"\nCities: {', '.join(sorted(cities))}")
    while True:
        c = input(prompt).strip().title()
        if c in cities:
            return c
        print("  Not found - check spelling.")


def main():
    ap = argparse.ArgumentParser(description="Route comparison engine")
    ap.add_argument("start", nargs="?")
    ap.add_argument("end", nargs="?")
    ap.add_argument("--fuel", type=float, default=8, help="Rs per km")
    ap.add_argument("--time-value", type=float, default=200, help="Rs per hour")
    ap.add_argument("--toll", type=float, default=1.0, help="toll weight")
    ap.add_argument("--k", type=int, default=4, help="routes to compare")
    a = ap.parse_args()

    eng = RouteEngine(ROADS, a.fuel, a.time_value, a.toll)
    start = a.start.title() if a.start else pick("From: ", eng.graph)
    end = a.end.title() if a.end else pick("To:   ", eng.graph)
    if start not in eng.graph or end not in eng.graph or start == end:
        raise SystemExit("Choose two different cities from the list.")
    routes = eng.k_routes(start, end, a.k)
    if not routes:
        raise SystemExit("No route found.")
    report(routes)


if __name__ == "__main__":
    main()
