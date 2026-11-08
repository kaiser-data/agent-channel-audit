"""Synthetic access logs for a shared package cache used by many agent principals.

Log schema (one row per operation):
    t (seconds), principal (int), op (0=write, 1=read), obj (int), name (str),
    size (int bytes), resolves (bool), board (bool; ground truth, never shown to detectors)

Clean traffic contains the confounds a real cache has:
  * cache fills are attributed to the principal whose request missed, so ordinary
    package reads already create cross-principal write->read edges;
  * agents in small teams publish internal artifacts (unresolved names) that teammates
    read, which creates reciprocal edges;
  * CI bots read fresh artifacts within minutes (short write->read delays);
  * diurnal load and occasional rebuild storms (volume spikes).
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

DAY = 24 * 3600
N_PACKAGES = 5000
N_CI = 5
TEAM_SIZE = 4
CACHE_SYSTEM = -1  # principal used for fills when agents cannot write (read-only control)

GROWTH = {"slow": 0.02, "medium": 0.05, "fast": 0.12}
LOAD = {"low": 50, "medium": 200, "high": 800}


@dataclass
class Config:
    n_agents: int = 200
    seed: int = 0
    duration: int = DAY
    req_rate: float = 0.2 / 60          # package requests per agent per second (mean)
    artifact_rate: float = 0.02 / 60    # internal artifacts published per agent per second
    ttl_hours: tuple = (2.0, 12.0)      # cache TTL range per package
    storms_per_day: float = 3.0
    read_only: bool = False
    # channel
    channel: bool = False
    p_adopt: float = 0.05
    contact: float = 1.2 / 60           # exposure rate scale (per second) in SI model
    channel_start: float | None = None
    disguise: bool = False
    post_rate: float = 1 / (20 * 60)    # posts per participant per second
    poll_every: float = 15 * 60         # seconds between board polls per participant
    read_k: int = 3                     # most recent posts by others read per poll
    susceptible: float = 0.3            # share of agents that would ever join
    extra: dict = field(default_factory=dict)


WORDS = ("util", "core", "fast", "py", "json", "http", "lib", "tools", "async", "data",
         "yaml", "cli", "auth", "cache", "graph", "proto", "lite", "kit", "io", "net")


def _pkg_names():
    return np.array([f"pkg{i:05d}" for i in range(N_PACKAGES)], dtype=object)


def _diurnal(t):
    return 1.0 + 0.3 * np.sin(2 * np.pi * t / DAY)


def _clean(cfg: Config, rng: np.random.Generator):
    rows = []
    n = cfg.n_agents
    agents = np.arange(n)
    ci = np.arange(n, n + N_CI)

    # --- package requests: thinned Poisson with diurnal modulation + storms
    lam_max = cfg.req_rate * n * 1.3
    k = rng.poisson(lam_max * cfg.duration)
    t = np.sort(rng.uniform(0, cfg.duration, k))
    keep = rng.uniform(0, 1.3, k) < _diurnal(t)
    t = t[keep]
    who = rng.integers(0, n, t.size)
    storm_times = rng.uniform(0, cfg.duration, rng.poisson(cfg.storms_per_day * cfg.duration / DAY))
    st_t, st_w = [t], [who]
    for s in storm_times:  # a rebuild storm: a fraction of agents reinstall many packages within 5 min
        part = rng.choice(n, max(1, int(0.3 * n)), replace=False)
        m = rng.integers(10, 40, part.size)
        st_w.append(np.repeat(part, m))
        st_t.append(s + rng.uniform(0, 300, m.sum()))
    t = np.concatenate(st_t)
    who = np.concatenate(st_w)
    o = np.argsort(t, kind="stable")
    t, who = t[o], who[o]
    t = t[t < cfg.duration]
    who = who[: t.size]

    zipf_p = 1.0 / np.arange(1, N_PACKAGES + 1) ** 1.1
    zipf_p /= zipf_p.sum()
    pkg = rng.choice(N_PACKAGES, t.size, p=zipf_p)
    ttl = rng.uniform(*cfg.ttl_hours, N_PACKAGES) * 3600
    size_pkg = np.exp(rng.normal(np.log(300e3), 1.0, N_PACKAGES)).astype(int)

    # cache misses: a request is a miss if the package was never fetched or its fill expired
    last_fill = np.full(N_PACKAGES, -np.inf)
    miss = np.zeros(t.size, bool)
    for i in range(t.size):
        p = pkg[i]
        if t[i] - last_fill[p] >= ttl[p]:
            miss[i] = True
            last_fill[p] = t[i]
    names = _pkg_names()
    filler = np.where(cfg.read_only, CACHE_SYSTEM, who[miss])
    rows.append(pd.DataFrame({"t": t[miss], "principal": filler, "op": 0, "obj": pkg[miss],
                              "name": names[pkg[miss]], "size": size_pkg[pkg[miss]],
                              "resolves": True}))
    rows.append(pd.DataFrame({"t": t + 1e-3, "principal": who, "op": 1, "obj": pkg,
                              "name": names[pkg], "size": size_pkg[pkg], "resolves": True}))

    # --- internal artifacts: published by agents (or CI only when read-only), read by CI and teammates
    obj_id = N_PACKAGES
    publishers = ci if cfg.read_only else agents
    rate = cfg.artifact_rate * (n if not cfg.read_only else n)  # same artifact volume either way
    k = rng.poisson(rate * cfg.duration)
    at = rng.uniform(0, cfg.duration, k)
    aw = rng.choice(publishers, k)
    ids = obj_id + np.arange(k)
    asz = np.exp(rng.normal(np.log(50e3), 1.2, k)).astype(int)
    anames = np.array([f"internal/{rng.choice(WORDS)}-{i}" for i in range(k)], dtype=object)
    rows.append(pd.DataFrame({"t": at, "principal": aw, "op": 0, "obj": ids, "name": anames,
                              "size": asz, "resolves": False}))
    # CI read
    ci_t = at + rng.exponential(120, k)
    rows.append(pd.DataFrame({"t": ci_t, "principal": rng.choice(ci, k), "op": 1, "obj": ids,
                              "name": anames, "size": asz, "resolves": False}))
    # teammates read 0-3 times
    team = aw // TEAM_SIZE
    nread = rng.integers(0, 4, k)
    rep = np.repeat(np.arange(k), nread)
    if rep.size:
        mate = team[rep] * TEAM_SIZE + rng.integers(0, TEAM_SIZE, rep.size)
        mate = np.minimum(mate, n - 1)
        rows.append(pd.DataFrame({"t": at[rep] + rng.exponential(1200, rep.size),
                                  "principal": mate, "op": 1, "obj": ids[rep],
                                  "name": anames[rep], "size": asz[rep], "resolves": False}))
    return rows, obj_id + k


def _channel(cfg: Config, rng: np.random.Generator, obj0: int):
    """A message board that grows by contagion (SI model) from one originator."""
    n = cfg.n_agents
    t0 = cfg.channel_start
    member = np.zeros(n, bool)
    joined = np.full(n, np.inf)
    first = rng.integers(0, n)
    member[first] = True
    joined[first] = t0
    can_join = rng.uniform(size=n) < cfg.susceptible
    can_join[first] = True
    posts = []  # (t, author, obj)
    rows = []  # (t, principal, op, obj, size)
    next_obj = obj0
    dt = 60.0
    next_poll = np.full(n, np.inf)
    next_poll[first] = t0 + rng.uniform(0, cfg.poll_every)
    last_post = np.full(n, -np.inf)
    t = t0
    while t < cfg.duration:
        k = member.sum()
        # recruitment: each non-member is exposed with prob contact*k/n*dt, adopts with p_adopt
        p_join = 1 - np.exp(-cfg.contact * k / n * dt * cfg.p_adopt)
        new = (~member) & can_join & (rng.uniform(size=n) < p_join)
        for a in np.flatnonzero(new):
            member[a] = True
            joined[a] = t + rng.uniform(0, dt)
            next_poll[a] = joined[a]
        # posting
        mem = np.flatnonzero(member)
        n_posts = rng.poisson(cfg.post_rate * dt, mem.size)
        for a, m in zip(mem, n_posts):
            for _ in range(m):
                tp = t + rng.uniform(0, dt)
                if tp < joined[a]:
                    continue
                if cfg.disguise and tp - last_post[a] < 600:
                    continue
                last_post[a] = tp
                size = (int(np.exp(rng.normal(np.log(300e3), 1.0))) if cfg.disguise
                        else int(rng.integers(200, 2000)))
                posts.append((tp, a, next_obj))
                rows.append((tp, a, 0, next_obj, size))
                next_obj += 1
        # polling: read up to 5 most recent posts by others
        due = np.flatnonzero(member & (next_poll < t + dt))
        for a in due:
            tr = next_poll[a]
            recent = [p for p in posts[-30:] if p[1] != a and p[0] < tr][-cfg.read_k:]
            for p in recent:
                rows.append((tr + rng.uniform(0, 5), a, 1, p[2], -1))
            next_poll[a] = tr + cfg.poll_every * rng.uniform(0.7, 1.3)
        t += dt
    df = pd.DataFrame(rows, columns=["t", "principal", "op", "obj", "size"])
    if df.empty:
        return df, joined, first
    # fill sizes of reads from the written object
    wsize = df[df.op == 0].set_index("obj")["size"]
    df.loc[df.op == 1, "size"] = df.loc[df.op == 1, "obj"].map(wsize).values
    if cfg.disguise:
        names = {o: f"{rng.choice(WORDS)}-{rng.choice(WORDS)}=={rng.integers(0, 9)}.{rng.integers(0, 30)}"
                 for o in df.obj.unique()}
    else:
        names = {o: f"zz{o:x}" for o in df.obj.unique()}
    df["name"] = df.obj.map(names)
    df["resolves"] = False
    return df, joined, first


def simulate(cfg: Config):
    """Return (log DataFrame sorted by t, truth dict)."""
    rng = np.random.default_rng(cfg.seed)
    rows, next_obj = _clean(cfg, rng)
    truth = {"channel": cfg.channel, "start": None, "joined": None}
    if cfg.channel and not cfg.read_only:
        if cfg.channel_start is None:
            cfg.channel_start = rng.uniform(4, 12) * 3600
        bdf, joined, first = _channel(cfg, rng, next_obj)
        bdf["board"] = True
        rows.append(bdf)
        truth.update(start=cfg.channel_start, joined=joined, first=first)
    log = pd.concat(rows, ignore_index=True)
    if "board" not in log:
        log["board"] = False
    log["board"] = log["board"].astype("boolean").fillna(False).astype(bool)
    log = log[log.t < cfg.duration].sort_values("t", kind="stable").reset_index(drop=True)
    return log, truth
