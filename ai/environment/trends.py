"""Historical telemetry trend analysis and rolling time-series window.
Agent 6 Ownership.
"""

from datetime import datetime, timezone
from typing import List, Optional, Deque, Union, Dict, Any
from collections import deque
import numpy as np

from ai.environment.schemas import TelemetryInput, TrendSummary, TrendDirection


class TelemetryHistoryBuffer:
    """Rolling memory buffer of recent telemetry snapshots for temporal gradient analysis."""

    def __init__(self, max_samples: int = 120, max_window_minutes: float = 60.0):
        self.max_samples = max_samples
        self.max_window_minutes = max_window_minutes
        self.buffer: Deque[TelemetryInput] = deque(maxlen=max_samples)

    def add_snapshot(self, telemetry: Union[TelemetryInput, Dict[str, Any]]) -> None:
        """Appends a new telemetry snapshot into the buffer."""
        if isinstance(telemetry, dict):
            item = TelemetryInput(**telemetry)
        else:
            item = telemetry
        self.buffer.append(item)

    def populate(self, history: List[Union[TelemetryInput, Dict[str, Any]]]) -> None:
        """Bulk initializes the buffer with historical telemetry frames."""
        self.buffer.clear()
        for item in history:
            self.add_snapshot(item)

    def count(self) -> int:
        return len(self.buffer)

    def analyze_trends(self) -> TrendSummary:
        """Analyzes moving rates of change and volatility across the buffer window."""
        if len(self.buffer) < 2:
            return TrendSummary()

        # Extract chronological arrays
        timestamps: List[float] = []
        lux_vals: List[float] = []
        press_vals: List[float] = []
        hum_vals: List[float] = []
        temp_vals: List[float] = []

        for item in self.buffer:
            try:
                dt = datetime.fromisoformat(str(item.timestamp).replace("Z", "+00:00"))
                ts = dt.timestamp()
            except Exception:
                ts = float(len(timestamps) * 60)

            timestamps.append(ts)
            lux_vals.append(float(item.lux))
            press_vals.append(float(item.pressure))
            hum_vals.append(float(item.humidity))
            temp_vals.append(float(item.temperature))

        t_arr = np.array(timestamps)
        # Normalize time to minutes relative to start
        t_minutes = (t_arr - t_arr[0]) / 60.0
        dt_total_min = t_minutes[-1] - t_minutes[0]

        if dt_total_min < 0.1:
            # Fallback if timestamps are identical
            t_minutes = np.arange(len(timestamps), dtype=float)
            dt_total_min = float(len(timestamps))

        dt_total_hours = max(0.01, dt_total_min / 60.0)

        # 1. Lux rate of change (lux / min) and volatility
        lux_slope = float(np.polyfit(t_minutes, lux_vals, 1)[0]) if len(lux_vals) >= 2 else 0.0
        lux_std = float(np.std(lux_vals))
        lux_mean = float(np.mean(lux_vals)) if np.mean(lux_vals) > 0 else 1.0
        lux_cov = lux_std / lux_mean

        if lux_cov > 0.35 and lux_mean > 5000:
            lux_trend = TrendDirection.VOLATILE
        elif lux_slope > 100.0:
            lux_trend = TrendDirection.RISING
        elif lux_slope < -100.0:
            lux_trend = TrendDirection.FALLING
        else:
            lux_trend = TrendDirection.STEADY

        # 2. Pressure trend (hPa / hour)
        press_slope_min = float(np.polyfit(t_minutes, press_vals, 1)[0]) if len(press_vals) >= 2 else 0.0
        press_change_hpa_hour = press_slope_min * 60.0

        if press_change_hpa_hour > 0.5:
            press_trend = TrendDirection.RISING
        elif press_change_hpa_hour < -0.5:
            press_trend = TrendDirection.FALLING
        else:
            press_trend = TrendDirection.STEADY

        # 3. Humidity trend (% / hour)
        hum_slope_min = float(np.polyfit(t_minutes, hum_vals, 1)[0]) if len(hum_vals) >= 2 else 0.0
        hum_change_pct_hour = hum_slope_min * 60.0

        if hum_change_pct_hour > 3.0:
            hum_trend = TrendDirection.RISING
        elif hum_change_pct_hour < -3.0:
            hum_trend = TrendDirection.FALLING
        else:
            hum_trend = TrendDirection.STEADY

        # 4. Temperature trend (deg C / hour)
        temp_slope_min = float(np.polyfit(t_minutes, temp_vals, 1)[0]) if len(temp_vals) >= 2 else 0.0
        temp_change_c_hour = temp_slope_min * 60.0

        if temp_change_c_hour > 1.0:
            temp_trend = TrendDirection.RISING
        elif temp_change_c_hour < -1.0:
            temp_trend = TrendDirection.FALLING
        else:
            temp_trend = TrendDirection.STEADY

        return TrendSummary(
            lux_trend=lux_trend,
            pressure_trend=press_trend,
            humidity_trend=hum_trend,
            temperature_trend=temp_trend,
            lux_change_rate_per_min=round(lux_slope, 2),
            pressure_change_hpa_per_hour=round(press_change_hpa_hour, 3),
            humidity_change_pct_per_hour=round(hum_change_pct_hour, 2)
        )
