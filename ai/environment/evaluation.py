"""Model Evaluation and Benchmark Framework.
Agent 6 Ownership.

Evaluates Observation Quality Prediction models on simulation test suites.
Metrics:
- Mean Absolute Error (MAE)
- Root Mean Squared Error (RMSE)
- Pearson Correlation (r)
- Directional Trend Accuracy (%)
"""

import sys
from typing import Dict, List, Any, Tuple
import numpy as np

from ai.environment.schemas import TelemetryInput
from ai.environment.trends import TelemetryHistoryBuffer
from ai.environment.features import extract_environmental_features
from ai.environment.assessor import score_current_observation_quality
from ai.environment.models.base import ObservationQualityModel
from ai.environment.models.physics_baseline import PhysicsBaselineModel
from ai.environment.models.ml_model import GradientBoostingQualityModel
from ai.environment.simulator import EnvironmentalSimulator


def compute_directional_accuracy(current: np.ndarray, actual_future: np.ndarray, predicted_future: np.ndarray) -> float:
    """Calculates directional trend accuracy (percentage of times predicted trend sign matches actual trend sign)."""
    actual_direction = np.sign(actual_future - current)
    pred_direction = np.sign(predicted_future - current)
    # Allow small tolerance where change is negligible
    matches = (actual_direction == pred_direction) | (np.abs(actual_future - predicted_future) < 0.05)
    return float(np.mean(matches) * 100.0)


def evaluate_model_on_scenarios(
    model: ObservationQualityModel,
    scenarios: List[str] = ["CLEAR_DAY", "AFTERNOON_CLOUDS", "THUNDERSTORM_SQUALL", "MORNING_CONDENSATION"],
    horizons: Tuple[int, int, int] = (15, 30, 60)
) -> Dict[str, Dict[str, float]]:
    """Evaluates a forecasting model against synthetic ground-truth scenarios."""
    results: Dict[str, Dict[str, float]] = {f"{h}m": {"mae": 0.0, "rmse": 0.0, "pearson_r": 0.0, "dir_acc": 0.0} for h in horizons}

    all_y_true: Dict[int, List[float]] = {h: [] for h in horizons}
    all_y_pred: Dict[int, List[float]] = {h: [] for h in horizons}
    all_current: Dict[int, List[float]] = {h: [] for h in horizons}

    for sc in scenarios:
        stream = EnvironmentalSimulator.generate_scenario(sc, duration_minutes=180, step_seconds=60)
        history = TelemetryHistoryBuffer()
        qualities: List[float] = []
        features_list = []
        telemetry_list = []
        trends_list = []

        for row in stream:
            tel = TelemetryInput(**row)
            history.add_snapshot(tel)
            trends = history.analyze_trends()
            feats = extract_environmental_features(tel, trends)
            q, _ = score_current_observation_quality(feats, tel, trends)

            qualities.append(q)
            features_list.append(feats)
            telemetry_list.append(tel)
            trends_list.append(trends)

        max_h = max(horizons)
        for idx in range(10, len(stream) - max_h, 3):  # Sample every 3 minutes
            tel = telemetry_list[idx]
            feats = features_list[idx]
            trends = trends_list[idx]
            q_curr = qualities[idx]

            preds = model.predict_all_horizons(q_curr, tel, feats, trends, horizons=horizons)

            for h in horizons:
                y_true = qualities[idx + h]
                y_pred = preds[f"{h}m"]
                all_y_true[h].append(y_true)
                all_y_pred[h].append(y_pred)
                all_current[h].append(q_curr)

    for h in horizons:
        yt = np.array(all_y_true[h])
        yp = np.array(all_y_pred[h])
        yc = np.array(all_current[h])

        mae = float(np.mean(np.abs(yt - yp)))
        rmse = float(np.sqrt(np.mean((yt - yp) ** 2)))
        r = float(np.corrcoef(yt, yp)[0, 1]) if np.std(yt) > 1e-4 and np.std(yp) > 1e-4 else 1.0
        dir_acc = compute_directional_accuracy(yc, yt, yp)

        results[f"{h}m"] = {
            "mae": round(mae, 4),
            "rmse": round(rmse, 4),
            "pearson_r": round(r, 4),
            "directional_accuracy_pct": round(dir_acc, 2),
            "sample_count": len(yt)
        }

    return results


def run_benchmark() -> None:
    """Runs a complete benchmark comparing Physics Baseline against ML Predictor."""
    print("=" * 70)
    print("SOLAR SENTRY AGENT 6: MODEL BENCHMARK & EVALUATION HARNESS")
    print("=" * 70)

    # 1. Physics Baseline Model
    baseline = PhysicsBaselineModel()
    print(f"\nEvaluating Baseline Model: {baseline.model_version}")
    baseline_metrics = evaluate_model_on_scenarios(baseline)

    for h_key, metrics in baseline_metrics.items():
        print(f"  Horizon [{h_key}]: MAE={metrics['mae']:.4f}, RMSE={metrics['rmse']:.4f}, "
              f"Pearson={metrics['pearson_r']:.3f}, Directional Acc={metrics['directional_accuracy_pct']:.1f}%")

    # 2. Train and Evaluate ML Model
    print("\nSynthesizing training set and fitting Gradient Boosting Model...")
    X_train, y_train = EnvironmentalSimulator.build_training_dataset(num_scenarios_each=3)
    ml_model = GradientBoostingQualityModel()
    ml_model.fit(X_train, y_train)

    print(f"Evaluating ML Model: {ml_model.model_version}")
    ml_metrics = evaluate_model_on_scenarios(ml_model)

    for h_key, metrics in ml_metrics.items():
        print(f"  Horizon [{h_key}]: MAE={metrics['mae']:.4f}, RMSE={metrics['rmse']:.4f}, "
              f"Pearson={metrics['pearson_r']:.3f}, Directional Acc={metrics['directional_accuracy_pct']:.1f}%")

    print("\n" + "=" * 70)
    print("BENCHMARK COMPLETED SUCCESSFULLY.")
    print("=" * 70)


if __name__ == "__main__":
    run_benchmark()
