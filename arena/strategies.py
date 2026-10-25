"""Three deliberately simple causal policies; coefficients are not fitted optima."""
from dataclasses import dataclass
import math
from .engine import Observation, Quote

STRATEGIES = ("Fixed", "Inventory", "Adaptive")


@dataclass(frozen=True)
class Strategy:
    name: str = "Adaptive"
    half_spread: float = 0.05
    skew: float = 0.015
    window: int = 30
    prior_vol: float = 0.04  # CU/sqrt(second), used only until 2 returns exist

    def __post_init__(self):
        if self.name not in STRATEGIES:
            raise ValueError("Unknown strategy")
        if not all(math.isfinite(v) for v in (self.half_spread,self.skew,self.prior_vol)):
            raise ValueError("Parameters must be finite")
        if self.half_spread <= 0 or self.skew < 0 or self.prior_vol <= 0 or self.window < 2:
            raise ValueError("Invalid strategy parameters")

    def vol_ratio(self, obs: Observation) -> float:
        # No demeaning: recent drift/jumps also increase the defensive width.
        prices = obs.past_mids[-(self.window+1):]
        n = len(prices)-1
        vol = self.prior_vol if n < 2 else math.sqrt(
            sum((b-a)**2 for a,b in zip(prices,prices[1:]))/(n*obs.dt))
        return max(0.5,min(3.0,vol/self.prior_vol))

    def quote(self, obs: Observation) -> Quote:
        ratio = self.vol_ratio(obs) if self.name == "Adaptive" else 1.0
        width = self.half_spread*ratio
        shift = 0.0 if self.name == "Fixed" else -self.skew*obs.inventory
        if self.name == "Adaptive":
            shift *= ratio**2
        center = obs.mid+shift
        return Quote(center-width,center+width)


@dataclass(frozen=True)
class Manual:
    half_spread: float
    offset: float
    bid_enabled: bool = True
    ask_enabled: bool = True

    def quote(self, obs: Observation) -> Quote:
        return Quote(obs.mid+self.offset-self.half_spread if self.bid_enabled else None,
                     obs.mid+self.offset+self.half_spread if self.ask_enabled else None)
