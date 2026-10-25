"""Auditable discrete-time simulator. No exchange connection or network access.

The exogenous tape belongs to the engine. Strategies receive an immutable
Observation containing only the reference prefix available at quote time.
"""
from dataclasses import dataclass, field, asdict
from typing import Protocol
import math
import numpy as np

SCENARIOS = ("Stable", "Trend", "High volatility", "Jump", "Adverse selection")


@dataclass(frozen=True)
class Config:
    steps: int = 600
    dt: float = 1.0
    initial_mid: float = 100.0
    initial_cash: float = 10000.0
    fee_bps: float = 0.5
    inventory_limit: int = 10
    arrival_rate: float = 0.8
    distance_decay: float = 15.0
    vol_multiplier: float = 1.0
    min_distance: float = 0.01
    max_distance: float = 5.0

    def __post_init__(self):
        for name, value in asdict(self).items():
            if not math.isfinite(value):
                raise ValueError(f"{name} must be finite")
        if not isinstance(self.steps, int) or not 1 <= self.steps <= 20000:
            raise ValueError("steps must be an integer in [1, 20000]")
        if not isinstance(self.inventory_limit, int) or not 1 <= self.inventory_limit <= 1000:
            raise ValueError("inventory_limit must be an integer in [1, 1000]")
        if not 0.01 <= self.dt <= 60 or not 1 <= self.initial_mid <= 1e6:
            raise ValueError("dt or initial_mid outside supported range")
        if not 0 <= self.fee_bps <= 100 or self.initial_cash <= 0:
            raise ValueError("Invalid fee/capital")
        if not 0 <= self.arrival_rate <= 100 or not 0 <= self.distance_decay <= 1000:
            raise ValueError("Invalid intensity/decay")
        if not 0 <= self.vol_multiplier <= 10:
            raise ValueError("Invalid volatility multiplier")
        if not 0 < self.min_distance < self.max_distance < self.initial_mid:
            raise ValueError("Invalid quote distance bounds")


@dataclass(frozen=True)
class Tape:
    mids: np.ndarray          # length steps+1; the engine alone reads the future
    directions: np.ndarray   # +1: customer buys from dealer; -1: customer sells
    arrival_u: np.ndarray
    acceptance_u: np.ndarray
    scenario: str
    seed: int


def make_tape(config: Config, scenario: str, seed: int) -> Tape:
    if scenario not in SCENARIOS:
        raise ValueError(f"Unknown scenario {scenario}")
    if not isinstance(seed, int) or not 0 <= seed < 2**32:
        raise ValueError("seed must be an integer in [0, 2**32)")
    rng = np.random.default_rng(seed)
    # Always draw the same number in the same order, independent of quotes/fills.
    eps = rng.standard_normal(config.steps)
    directions = rng.choice([-1, 1], size=config.steps)
    arrival_u = rng.random(config.steps)
    acceptance_u = rng.random(config.steps)
    jump_sign = int(rng.choice([-1, 1]))  # independent, drawn in every scenario
    sigma = np.full(config.steps, 0.0004 * config.vol_multiplier)
    drift = 0.00006 if scenario == "Trend" else 0.0
    shocks = eps
    if scenario == "High volatility":
        # Horizon fractions correspond to 150-second blocks at default settings.
        block = max(1, config.steps // 4)
        sigma[(np.arange(config.steps) // block) % 2 == 1] *= 3.5
    if scenario == "Adverse selection":
        sigma *= 2
        rho = 0.85
        shocks = math.sqrt(1-rho*rho) * eps + rho * directions
    increments = (drift - sigma*sigma/2)*config.dt + sigma*math.sqrt(config.dt)*shocks
    if scenario == "Jump":
        # Independent sign avoids a relationship with a later innovation.
        increments[config.steps//2] += 0.016 * jump_sign
    mids = config.initial_mid * np.exp(np.r_[0.0, np.cumsum(increments)])
    if not np.isfinite(mids).all() or mids.min() < 0.1 or mids.max() > 1e8:
        raise ValueError("Price path leaves supported numerical range; reduce horizon/volatility")
    for a in (mids, directions, arrival_u, acceptance_u):
        a.setflags(write=False)
    return Tape(mids, directions, arrival_u, acceptance_u, scenario, seed)


@dataclass(frozen=True)
class Observation:
    step: int
    dt: float
    mid: float
    inventory: int
    cash: float
    past_mids: tuple[float, ...]  # includes current mid, never S[t+1]


@dataclass(frozen=True)
class Quote:
    bid: float | None
    ask: float | None


class Policy(Protocol):
    def quote(self, obs: Observation) -> Quote: ...


def bound_quote(quote: Quote, mid: float, config: Config) -> Quote:
    # Continuous prices; no fictitious queue priority or tick-size model.
    minimum = min(config.min_distance, mid * 0.01)
    maximum = min(config.max_distance, mid * 0.2)
    def clamp(value, low, high):
        if value is None:
            return None
        if not math.isfinite(value):
            raise ValueError("Nonfinite quote")
        return max(low, min(high, value))
    return Quote(clamp(quote.bid, mid-maximum, mid-minimum),
                 clamp(quote.ask, mid+minimum, mid+maximum))


@dataclass
class Ledger:
    config: Config
    cash: float = field(init=False)
    inventory: int = 0
    fees: float = 0.0
    spread_capture: float = 0.0
    holding_pnl: float = 0.0
    fills: list = field(default_factory=list)
    history: list = field(default_factory=list)
    arrivals: int = 0
    cap_blocked: int = 0
    paused_arrivals: int = 0

    def __post_init__(self):
        self.cash = self.config.initial_cash
        self.history.append(dict(step=0, time_s=0.0, mid=self.config.initial_mid,
                                 cash=self.cash, inventory=0, equity=self.cash, pnl=0.0,
                                 fees=0.0, bid=None, ask=None, fill=""))

    def fill(self, side: str, price: float, mid: float, step: int):
        if side not in ("buy", "sell") or price <= 0 or not math.isfinite(price):
            raise ValueError("Invalid execution")
        dq = 1 if side == "buy" else -1
        if abs(self.inventory+dq) > self.config.inventory_limit:
            raise ValueError("Execution would violate inventory cap")
        fee = price * self.config.fee_bps / 10000
        self.cash -= dq * price + fee
        self.inventory += dq
        self.fees += fee
        self.spread_capture += dq * (mid-price)
        self.fills.append(dict(step=step, side=side, price=price, quantity=1,
                               fee=fee, inventory=self.inventory, cash=self.cash))

    def metrics(self) -> dict:
        equity = np.array([x["equity"] for x in self.history])
        inventory = np.array([x["inventory"] for x in self.history])
        pnl = float(equity[-1] - self.config.initial_cash)
        decomposition_error = pnl - (self.spread_capture+self.holding_pnl-self.fees)
        # Independently reconstruct terminal cash/inventory from executions.
        signed_notional = sum((1 if x["side"] == "buy" else -1)*x["price"] for x in self.fills)
        cash_error = self.cash - (self.config.initial_cash-signed_notional-self.fees)
        q_check = sum(1 if x["side"] == "buy" else -1 for x in self.fills)
        if abs(decomposition_error) > 1e-6 or abs(cash_error) > 1e-6 or q_check != self.inventory:
            raise AssertionError("Accounting identity failed")
        return dict(pnl=pnl, max_drawdown=float(np.max(np.maximum.accumulate(equity)-equity)),
                    avg_abs_inventory=float(np.mean(np.abs(inventory[1:]))) if len(inventory)>1 else 0.0,
                    max_abs_inventory=int(np.max(np.abs(inventory))), fills=len(self.fills),
                    volume=len(self.fills), fees=self.fees, terminal_inventory=self.inventory,
                    arrivals=self.arrivals, cap_blocked=self.cap_blocked,
                    paused_arrivals=self.paused_arrivals,
                    fill_rate=len(self.fills)/self.arrivals if self.arrivals else 0.0,
                    spread_capture=self.spread_capture, holding_pnl=self.holding_pnl,
                    accounting_error=max(abs(decomposition_error),abs(cash_error)))


def observe(tape: Tape, ledger: Ledger, step: int) -> Observation:
    return Observation(step, ledger.config.dt, float(tape.mids[step]),
                       ledger.inventory, ledger.cash, tuple(tape.mids[:step+1]))


def advance(tape: Tape, ledger: Ledger, quote: Quote, step: int) -> Quote:
    """Quote -> customer arrival/direction -> acceptance -> fill -> reference move.

    Every quote is cancelled/replaced on the next step. At most one unit fills.
    Inventory after the fill is held across the subsequent price move.
    """
    c = ledger.config
    if step != len(ledger.history)-1 or not 0 <= step < c.steps:
        raise ValueError("Steps must advance consecutively")
    mid, next_mid = float(tape.mids[step]), float(tape.mids[step+1])
    q = bound_quote(quote, mid, c)
    # Disable sides at quote time. Never allow later acceptance to breach a cap.
    bid = q.bid if ledger.inventory < c.inventory_limit else None
    ask = q.ask if ledger.inventory > -c.inventory_limit else None
    execution = ""
    if tape.arrival_u[step] < -math.expm1(-c.arrival_rate*c.dt):
        ledger.arrivals += 1
        customer_buy = tape.directions[step] == 1
        price = ask if customer_buy else bid
        cap = (customer_buy and ledger.inventory <= -c.inventory_limit) or (
            not customer_buy and ledger.inventory >= c.inventory_limit)
        if cap:
            ledger.cap_blocked += 1
        elif price is None:
            ledger.paused_arrivals += 1
        else:
            distance = price-mid if customer_buy else mid-price
            if tape.acceptance_u[step] < math.exp(-c.distance_decay*distance):
                execution = "sell" if customer_buy else "buy"
                ledger.fill(execution, price, mid, step+1)
    ledger.holding_pnl += ledger.inventory*(next_mid-mid)
    equity = ledger.cash + ledger.inventory*next_mid
    ledger.history.append(dict(step=step+1,time_s=(step+1)*c.dt,mid=next_mid,
                               cash=ledger.cash,inventory=ledger.inventory,equity=equity,
                               pnl=equity-c.initial_cash,fees=ledger.fees,bid=bid,ask=ask,
                               fill=execution))
    return Quote(bid, ask)


def simulate(config: Config, tape: Tape, policy: Policy) -> Ledger:
    if len(tape.mids) != config.steps+1 or not math.isclose(tape.mids[0],config.initial_mid):
        raise ValueError("Tape/config mismatch")
    ledger = Ledger(config)
    for step in range(config.steps):
        advance(tape,ledger,policy.quote(observe(tape,ledger,step)),step)
    ledger.metrics()  # enforce accounting for every run
    return ledger
