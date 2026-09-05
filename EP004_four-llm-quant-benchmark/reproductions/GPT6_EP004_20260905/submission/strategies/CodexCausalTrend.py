"""EP004 original candidate; six-epoch Hyperopt selected window=180, band=1.0."""
from pandas import DataFrame
from freqtrade.strategy import IStrategy, CategoricalParameter


class CodexCausalTrend(IStrategy):
    INTERFACE_VERSION = 3
    timeframe = "4h"
    can_short = True
    process_only_new_candles = True
    startup_candle_count = 182
    stoploss = -0.10
    minimal_roi = {"0": 100.0}
    use_exit_signal = True
    exit_profit_only = False
    trailing_stop = False
    position_adjustment_enable = False

    # 3 x 2 = 6 hypotheses; no data-driven choice has yet been made.
    trend_window = CategoricalParameter([60, 120, 180], default=120,
                                        space="buy", optimize=True)
    entry_band = CategoricalParameter([0.5, 1.0], default=1.0,
                                      space="buy", optimize=True)
    buy_params = {"trend_window": 180, "entry_band": 1.0}

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Precompute every candidate; buy-space hyperopt need not rerun this method.
        close = dataframe["close"]
        previous_close = close.shift(1)
        tr = DataFrame({
            "range": dataframe["high"] - dataframe["low"],
            "high_gap": (dataframe["high"] - previous_close).abs(),
            "low_gap": (dataframe["low"] - previous_close).abs(),
        }).max(axis=1)
        dataframe["atr_prior"] = tr.rolling(30, min_periods=30).mean().shift(1)
        dataframe["close_prior"] = close.shift(1)
        dataframe["volume_prior"] = dataframe["volume"].shift(1)
        for window in [60, 120, 180]:
            dataframe[f"mean_prior_{window}"] = close.rolling(
                window, min_periods=window).mean().shift(1)
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        center = dataframe[f"mean_prior_{int(self.trend_window.value)}"]
        band = float(self.entry_band.value) * dataframe["atr_prior"]
        eligible = (dataframe["volume_prior"] > 0) & (dataframe["atr_prior"] > 0)
        dataframe["enter_long"] = 0
        dataframe["enter_short"] = 0
        dataframe.loc[eligible & (dataframe["close_prior"] > center + band),
                      "enter_long"] = 1
        dataframe.loc[eligible & (dataframe["close_prior"] < center - band),
                      "enter_short"] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        center = dataframe[f"mean_prior_{int(self.trend_window.value)}"]
        dataframe["exit_long"] = 0
        dataframe["exit_short"] = 0
        dataframe.loc[dataframe["close_prior"] < center, "exit_long"] = 1
        dataframe.loc[dataframe["close_prior"] > center, "exit_short"] = 1
        return dataframe
