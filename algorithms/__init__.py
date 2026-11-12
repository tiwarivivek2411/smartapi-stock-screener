from .base_screener_algo import BaseScreenerAlgo, Candidate
from .volatility_squeeze import VolatilitySqueezeAlgo
from .relative_strength import RelativeStrengthAlgo
from .ema_ribbon import EMARibbonAlgo
from .vwap_reversion import VWAPReversionAlgo
from .vol_adjusted_trend import VolAdjustedTrendAlgo
from .orb_squeeze import ORBSqueezeAlgo
from .bull_bear_pennant import BullBearPennantAlgo
from .flat_level_triangle import FlatLevelTriangleAlgo
from .fakeout_trap import FakeoutTrapAlgo
from .cup_and_handle import CupAndHandleAlgo
from .vsa_no_supply import VolumeSpreadAnalysisAlgo
from .supertrend_vwap import SupertrendVWAPConfluenceAlgo
from .donchian_breakout import DonchianBreakoutAlgo
from .vpt_surge import VPTSurgeAlgo
from .macd_momentum import MACDMomentumAlgo
from .double_bottom import DoubleBottomAlgo
from .falling_wedge import FallingWedgeAlgo
from .adx_trend import ADXTrendAlgo
from .channel_compression import ChannelCompressionAlgo
from .rsi_range_expansion import RSIRangeExpansionAlgo
from .institutional_swing_confluence import InstitutionalSwingConfluenceAlgo
from .intraday_vwap_momentum import IntradayVWAPMomentumAlgo
from .liquidity_sweep_reversal import LiquiditySweepReversalAlgo
from .intraday_short_breakdown import IntradayShortBreakdownAlgo
from .keltner_vwap_reversion import KeltnerVWAPReversionAlgo
from .opening_range_breakout_dual import OpeningRangeBreakoutDualAlgo
from .supertrend_vwap_short import SupertrendVWAPShortAlgo
from .intraday_gap_down_continuation import IntradayGapDownContinuationAlgo

ALGORITHM_REGISTRY = {
    "squeeze": VolatilitySqueezeAlgo,
    "relative_strength": RelativeStrengthAlgo,
    "ema_ribbon": EMARibbonAlgo,
    "vwap_reversion": VWAPReversionAlgo,
    "vol_trend": VolAdjustedTrendAlgo,
    "orb_squeeze": ORBSqueezeAlgo,
    "pennant": BullBearPennantAlgo,
    "flat_level": FlatLevelTriangleAlgo,
    "fakeout_trap": FakeoutTrapAlgo,
    "cup_and_handle": CupAndHandleAlgo,
    "vsa_no_supply": VolumeSpreadAnalysisAlgo,
    "supertrend_vwap": SupertrendVWAPConfluenceAlgo,
    "donchian_breakout": DonchianBreakoutAlgo,
    "vpt_surge": VPTSurgeAlgo,
    "macd_momentum": MACDMomentumAlgo,
    "double_bottom": DoubleBottomAlgo,
    "falling_wedge": FallingWedgeAlgo,
    "adx_trend": ADXTrendAlgo,
    "channel_compression": ChannelCompressionAlgo,
    "rsi_range_expansion": RSIRangeExpansionAlgo,
    "institutional_swing_confluence": InstitutionalSwingConfluenceAlgo,
    "intraday_vwap_momentum": IntradayVWAPMomentumAlgo,
    "liquidity_sweep_reversal": LiquiditySweepReversalAlgo,
    "intraday_short_breakdown": IntradayShortBreakdownAlgo,
    "keltner_vwap_reversion": KeltnerVWAPReversionAlgo,
    "opening_range_breakout_dual": OpeningRangeBreakoutDualAlgo,
    "supertrend_vwap_short": SupertrendVWAPShortAlgo,
    "intraday_gap_down_continuation": IntradayGapDownContinuationAlgo
}

__all__ = [
    "BaseScreenerAlgo",
    "Candidate",
    "VolatilitySqueezeAlgo",
    "RelativeStrengthAlgo",
    "EMARibbonAlgo",
    "VWAPReversionAlgo",
    "VolAdjustedTrendAlgo",
    "ORBSqueezeAlgo",
    "BullBearPennantAlgo",
    "FlatLevelTriangleAlgo",
    "FakeoutTrapAlgo",
    "CupAndHandleAlgo",
    "VolumeSpreadAnalysisAlgo",
    "SupertrendVWAPConfluenceAlgo",
    "DonchianBreakoutAlgo",
    "VPTSurgeAlgo",
    "MACDMomentumAlgo",
    "DoubleBottomAlgo",
    "FallingWedgeAlgo",
    "ADXTrendAlgo",
    "ChannelCompressionAlgo",
    "RSIRangeExpansionAlgo",
    "InstitutionalSwingConfluenceAlgo",
    "IntradayVWAPMomentumAlgo",
    "LiquiditySweepReversalAlgo",
    "IntradayShortBreakdownAlgo",
    "KeltnerVWAPReversionAlgo",
    "OpeningRangeBreakoutDualAlgo",
    "SupertrendVWAPShortAlgo",
    "IntradayGapDownContinuationAlgo",
    "ALGORITHM_REGISTRY"
]
