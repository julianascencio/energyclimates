"""Reproducible, area-weighted clustering with spatial holdout diagnostics.

Models are plain JSON numeric arrays, never executable pickle/joblib payloads.
Cluster fit scores describe climate-feature geometry, not proven energy value.
"""

import hashlib
import json
from pathlib import Path
import platform
import numpy as np
import pandas as pd
from .rules import TECH_FEATURES, load_rules, classify_features


def spatial_blocks(frame, degrees=10):
    if not {"latitude", "longitude"}.issubset(frame):
        raise ValueError("Spatial evaluation requires latitude and longitude")
    lat = np.asarray(frame.latitude, float)
    lon = np.asarray(frame.longitude, float)
    if (
        not np.isfinite(lat).all()
        or not np.isfinite(lon).all()
        or (abs(lat) > 90).any()
        or (abs(lon) > 180).any()
    ):
        raise ValueError("Invalid evaluation coordinates")
    return np.floor((lat + 90) / degrees).astype(int) * (int(360 / degrees) + 1) + np.floor(
        (lon + 180) / degrees
    ).astype(int)


def weights_for(frame, area_weighted):
    if area_weighted:
        if "latitude" not in frame:
            raise ValueError("Area weighting requires latitude on a regular geographic grid")
        return np.maximum(np.cos(np.deg2rad(frame.latitude.to_numpy(float))), 1e-6)
    return np.ones(len(frame))


def _fit(x, weights, k, seed):
    from sklearn.cluster import MiniBatchKMeans
    from sklearn.preprocessing import StandardScaler

    scaler = StandardScaler().fit(x, sample_weight=weights)
    z = scaler.transform(x)
    estimator = MiniBatchKMeans(
        n_clusters=k,
        n_init=10,
        batch_size=4096,
        max_iter=300,
        random_state=seed,
        reassignment_ratio=0,
    ).fit(z, sample_weight=weights)
    return scaler, estimator


def _names(features, labels, k, technology, weights, rules):
    # Describe centres with ordinary words; retain distinct numbers in technical metadata only.
    centres = []
    numeric = features.select_dtypes(include="number").columns
    for i in range(k):
        mask = labels == i
        centres.append(
            {
                key: float(np.average(features.loc[mask, key], weights=weights[mask]))
                for key in numeric
                if np.isfinite(features.loc[mask, key]).all()
            }
        )
    summaries = pd.DataFrame(centres)
    basic = classify_features(summaries, technology, rules).zone_name.tolist()
    seen = {name: basic.count(name) for name in set(basic)}
    names = []
    for i, name in enumerate(basic):
        if seen[name] > 1:
            if technology == "bess":
                name += f" · summer {summaries.iloc[i].temperature_warmest_month_c:.0f}°C"
            else:
                name += f" · weak-month sun {100 * summaries.iloc[i].weak_month_ratio:.0f}%"
        names.append(name)
    # An unusually homogeneous input may still yield identical human descriptors.
    # Include a meaningful centre value instead of inventing a new climate name.
    for i, name in enumerate(names.copy()):
        if names.count(name) > 1:
            value = summaries.iloc[i][TECH_FEATURES[technology][0]]
            names[i] = (
                name + f" · {value:.2f}" + ("°C winter" if technology == "bess" else " kWh/m²/year")
            )
    return names, centres


def train_clusters(
    features,
    technology="pv",
    clusters=8,
    seed=42,
    area_weighted=False,
    feature_columns=None,
    rules=None,
):
    from sklearn import __version__ as sklearn_version
    from sklearn.model_selection import GroupShuffleSplit
    from sklearn.metrics import silhouette_score, adjusted_rand_score
    from threadpoolctl import threadpool_limits

    if technology not in TECH_FEATURES:
        raise ValueError("Technology must be pv, hybrid or bess")
    cols = list(feature_columns or TECH_FEATURES[technology])
    if len(cols) != len(set(cols)) or not cols:
        raise ValueError("Features must be unique and nonempty")
    forbidden = {
        "latitude",
        "longitude",
        "location_id",
        "zone_id",
        "pv_zone_id",
        "kgpv_zone_id",
        "target",
        "yield",
        "energy_yield",
        "pv_yield_kwh_kwp",
    }
    if forbidden.intersection(cols) or any(
        "zone" in c or "target" in c or "yield" in c for c in cols
    ):
        raise ValueError("Geography, labels and targets are not climate predictors")
    for c in cols + TECH_FEATURES[technology]:
        if c not in features:
            raise ValueError(f"Missing feature {c}")
    valid = np.isfinite(features[list(set(cols + TECH_FEATURES[technology]))].to_numpy(float)).all(
        1
    )
    f = features.loc[valid].reset_index(drop=True)
    x = f[cols].to_numpy(float)
    if not isinstance(clusters, int) or not 2 <= clusters <= 24:
        raise ValueError("Use 2–24 clusters")
    if len(f) < max(50, clusters * 10):
        raise ValueError(
            f"Need at least {max(50, clusters * 10)} complete locations; prediction with an existing model works for one location"
        )
    if np.unique(x, axis=0).shape[0] < clusters:
        raise ValueError("Fewer distinct climates than clusters")
    groups = spatial_blocks(f)
    if len(np.unique(groups)) < 5:
        raise ValueError(
            "Training needs at least five distinct 10° geographic blocks for spatial holdout"
        )
    train, test = next(
        GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=seed).split(x, groups=groups)
    )
    if len(train) < clusters * 3 or len(test) < max(clusters, 10):
        raise ValueError(
            "Insufficient geographic holdout; use more spatially distributed data or fewer clusters"
        )
    weights = weights_for(f, area_weighted)
    rules = rules or load_rules()
    with threadpool_limits(limits=1):
        # Evaluate without fitting the scaler or clusters on held-out geographic blocks.
        scaler_eval, estimator_eval = _fit(x[train], weights[train], clusters, seed)
        ztest = scaler_eval.transform(x[test])
        test_labels = estimator_eval.predict(ztest)
        error = ((ztest - estimator_eval.cluster_centers_[test_labels]) ** 2).sum(1)
        rng = np.random.default_rng(seed)
        subset = rng.choice(len(test), min(1500, len(test)), replace=False)
        unique = np.unique(test_labels[subset])
        silhouette = (
            float(silhouette_score(ztest[subset], test_labels[subset]))
            if 1 < len(unique) < len(subset)
            else None
        )
        # Stability across random initializations evaluated on the same held-out points.
        stability = []
        for extra in [1, 2]:
            ss, ee = _fit(x[train], weights[train], clusters, seed + extra)
            stability.append(
                float(adjusted_rand_score(test_labels, ee.predict(ss.transform(x[test]))))
            )
        scaler, estimator = _fit(x, weights, clusters, seed)
        labels = estimator.predict(scaler.transform(x))
    if len(np.unique(labels)) != clusters:
        raise ValueError("Empty fitted clusters; reduce cluster count")
    # Ordered by interpretable physical features, independent of arbitrary sklearn IDs.
    physical = scaler.inverse_transform(estimator.cluster_centers_)
    order = np.lexsort(tuple(physical[:, i] for i in range(len(cols) - 1, -1, -1)))
    remap = np.empty(clusters, dtype=int)
    remap[order] = np.arange(clusters)
    labels = remap[labels]
    centres = estimator.cluster_centers_[order]
    names, summaries = _names(f, labels, clusters, technology, weights, rules)
    z = scaler.transform(x)
    distance = np.sqrt(((z - centres[labels]) ** 2).sum(1))
    thresholds = [float(np.quantile(distance[labels == i], 0.95)) for i in range(clusters)]
    digest = hashlib.sha256(
        pd.util.hash_pandas_object(
            f[["latitude", "longitude"] + cols], index=False
        ).values.tobytes()
    ).hexdigest()
    model_digest = hashlib.sha256(
        json.dumps(
            {
                "input": digest,
                "features": cols,
                "area_weighted": area_weighted,
                "rules": rules,
                "k": clusters,
                "seed": seed,
            },
            sort_keys=True,
        ).encode()
    ).hexdigest()
    diagnostics = {
        "spatial_block_degrees": 10,
        "training_locations": len(train),
        "holdout_locations": len(test),
        "training_blocks": len(np.unique(groups[train])),
        "holdout_blocks": len(np.unique(groups[test])),
        "overlapping_blocks": len(set(groups[train]) & set(groups[test])),
        "holdout_mean_squared_feature_distance": float(np.average(error, weights=weights[test])),
        "holdout_silhouette_unweighted": silhouette,
        "silhouette_sample_size": len(subset),
        "initialization_stability_ari": stability,
        "rows_excluded_missing_features": int((~valid).sum()),
        "interpretation": "Feature-space diagnostics only. No energy-yield, battery-life or economic superiority has been established.",
    }
    model = {
        "schema": "energy-climate-kmeans-v1",
        "technology": technology,
        "model_version": f"{technology}-{model_digest[:12]}",
        "status": "experimental",
        "features": cols,
        "mean": scaler.mean_.tolist(),
        "scale": scaler.scale_.tolist(),
        "centres": centres.tolist(),
        "names": names,
        "cluster_feature_means": summaries,
        "radius95": thresholds,
        "feature_min": x.min(0).tolist(),
        "feature_max": x.max(0).tolist(),
        "seed": seed,
        "clusters": clusters,
        "area_weighted": area_weighted,
        "training_locations": len(f),
        "training_sha256": digest,
        "period": features.attrs.get("period", "Not supplied"),
        "rules": rules,
        "diagnostics": diagnostics,
        "implementation": {
            "python": platform.python_version(),
            "sklearn": sklearn_version,
            "algorithm": "MiniBatchKMeans",
            "n_init": 10,
            "batch_size": 4096,
            "threads": 1,
        },
    }
    return model, predict_clusters(features, model)


def validate_model(model):
    if model.get("schema") != "energy-climate-kmeans-v1":
        raise ValueError("Unsupported model schema")
    cols = model.get("features", [])
    k = model.get("clusters", 0)
    if not 1 <= len(cols) <= 100 or len(set(cols)) != len(cols) or not 2 <= k <= 24:
        raise ValueError("Invalid model dimensions")
    for name, shape in [
        ("mean", (len(cols),)),
        ("scale", (len(cols),)),
        ("centres", (k, len(cols))),
        ("radius95", (k,)),
        ("feature_min", (len(cols),)),
        ("feature_max", (len(cols),)),
    ]:
        arr = np.asarray(model[name], float)
        if arr.shape != shape or not np.isfinite(arr).all():
            raise ValueError(f"Invalid model array: {name}")
    if (np.asarray(model["scale"]) <= 0).any() or (np.asarray(model["radius95"]) < 0).any():
        raise ValueError("Invalid model scale or distance threshold")
    if len(model["names"]) != k or not all(isinstance(x, str) for x in model["names"]):
        raise ValueError("Invalid model labels")
    return model


def save_model(model, path):
    validate_model(model)
    Path(path).write_text(json.dumps(model, ensure_ascii=False, indent=2, allow_nan=False))


def load_model(path):
    path = Path(path)
    if path.stat().st_size > 5_000_000:
        raise ValueError("Model file is too large")
    return validate_model(json.loads(path.read_text()))


def predict_clusters(features, model, batch_size=10000):
    model = validate_model(model)
    cols = model["features"]
    for c in cols:
        if c not in features:
            raise ValueError(f"Missing model feature: {c}")
    x = features[cols].to_numpy(float)
    valid = np.isfinite(x).all(1)
    result = features[[c for c in ["location_id", "latitude", "longitude"] if c in features]].copy()
    code = np.zeros(len(x), int)
    distance = np.full(len(x), np.nan)
    gap = distance.copy()
    novel = np.zeros(len(x), bool)
    indexes = np.flatnonzero(valid)
    centre = np.asarray(model["centres"])
    mean = np.asarray(model["mean"])
    scale = np.asarray(model["scale"])
    for start in range(0, len(indexes), batch_size):
        idx = indexes[start : start + batch_size]
        z = (x[idx] - mean) / scale
        d = np.sqrt(((z[:, None, :] - centre[None, :, :]) ** 2).sum(2))
        nearest = np.argmin(d, axis=1)
        first = d[np.arange(len(idx)), nearest]
        two = np.partition(d, 1, axis=1)[:, :2]
        second = two.max(1)
        code[idx] = nearest + 1
        distance[idx] = first
        gap[idx] = (second - first) / np.maximum(second, 1e-12)
        novel[idx] = (
            (x[idx] < model["feature_min"]).any(1)
            | (x[idx] > model["feature_max"]).any(1)
            | (first > np.asarray(model["radius95"])[nearest])
        )
    result["zone_id"] = code
    result["zone_name"] = [model["names"][n - 1] if n else "Insufficient data" for n in code]
    result["feature_distance"] = distance
    result["assignment_separation"] = gap
    result["status"] = np.where(
        ~valid,
        "Insufficient data",
        np.where(
            novel, "Outside typical training conditions", "Within typical training conditions"
        ),
    )
    result["model_version"] = model["model_version"]
    return result


def evaluate_target(features, target_column, technology="pv", seed=42, folds=5):
    """Optional held-out prediction/feature relevance using an independent target.

    The caller must supply measured/simulated PV yield or BESS/HVAC outcome with
    documented period, system configuration and provenance. No target is invented.
    """
    from sklearn.ensemble import RandomForestRegressor
    from sklearn.model_selection import GroupKFold
    from sklearn.metrics import mean_absolute_error, root_mean_squared_error, r2_score
    from sklearn.inspection import permutation_importance

    cols = TECH_FEATURES[technology]
    if target_column in cols:
        raise ValueError("Target cannot also be a climate predictor")
    if target_column not in features:
        raise ValueError("Supply an independent outcome column")
    valid = np.isfinite(features[cols + [target_column]].to_numpy(float)).all(1)
    f = features.loc[valid].reset_index(drop=True)
    groups = spatial_blocks(f)
    if len(f) < 50 or len(np.unique(groups)) < folds:
        raise ValueError("Not enough complete locations or geographic groups")
    records = []
    importance = []
    for i, (train, test) in enumerate(GroupKFold(n_splits=folds).split(f, groups=groups)):
        model = RandomForestRegressor(
            n_estimators=150, min_samples_leaf=3, max_depth=20, random_state=seed, n_jobs=1
        )
        model.fit(f.iloc[train][cols], f.iloc[train][target_column])
        y = f.iloc[test][target_column]
        yp = model.predict(f.iloc[test][cols])
        base = float(f.iloc[train][target_column].mean())
        records.append(
            {
                "fold": i,
                "train_rows": len(train),
                "test_rows": len(test),
                "rmse": float(root_mean_squared_error(y, yp)),
                "baseline_rmse": float(root_mean_squared_error(y, np.full(len(y), base))),
                "mae": float(mean_absolute_error(y, yp)),
                "r2": float(r2_score(y, yp)) if len(y) > 1 and np.var(y) > 0 else None,
            }
        )
        score = permutation_importance(
            model,
            f.iloc[test][cols],
            y,
            n_repeats=3,
            scoring="neg_mean_absolute_error",
            random_state=seed,
        )
        importance.append(score.importances_mean)
    return {
        "target": target_column,
        "technology": technology,
        "rows": len(f),
        "excluded_rows": int((~valid).sum()),
        "spatial_block_degrees": 10,
        "folds": records,
        "permutation_importance_mae": dict(zip(cols, np.mean(importance, axis=0).tolist())),
        "note": "No feature selection used held-out outcomes. Inspect target provenance, spatial coverage and system confounders before interpreting climate relevance.",
    }
