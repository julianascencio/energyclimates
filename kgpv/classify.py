"""Published 2019 Fig. A1 ordering and Table 4 class merging.

No population reranking: retaining the published lookup isolates climate/input changes.
Temperature climatology is the equal-weight mean of calendar-month means, following KG.
At exact thresholds use inclusive boundaries explicitly shown in Fig. A1.
"""
import numpy as np

TP_LABELS = ["", "A", "B", "C", "D", "E", "F"]
ZONE_LABELS = ["", "AK", "AH", "BK", "BH", "CK", "CH", "DH", "DM", "DL", "EM", "EL", "FL"]
COLORS = ["#00000000", "#ff7657", "#bd0030", "#ffcd00", "#ff9f00", "#a493c5", "#81258e", "#93cf91", "#00965e", "#00592d", "#55a9cf", "#075da8", "#969696"]
MERGE = {"A": ["AH", "AH", "AH", "AK"], "B": ["BH", "BH", "BH", "BK"],
         "C": ["CH", "CH", "CH", "CK"], "D": ["DL", "DM", "DH", "DH"],
         "E": ["EL", "EM", "EM", "EM"], "F": ["FL", "FL", "FL", "FL"]}

def tp_classify(temperature, precipitation, latitude):
    """Arrays: (12, lat, lon); temperature °C, precipitation mm/month.

    Summer is Apr–Sep in the north, Oct–Mar in the south. Dryness threshold in mm:
    20*T + 280 if >=2/3 summer rain; +0 if >=2/3 winter rain; +140 otherwise.
    Polar takes precedence, then desert/steppe, then tropical/temperate/cold.
    Missing months produce no-data. Negative precipitation is invalid.
    """
    t, p = np.asarray(temperature, float), np.asarray(precipitation, float)
    if t.shape != p.shape or t.ndim != 3 or t.shape[0] != 12:
        raise ValueError("Expected matching (12, latitude, longitude) monthly arrays")
    lat = np.asarray(latitude)
    if lat.shape != (t.shape[1],):
        raise ValueError("Latitude axis does not match input grid")
    valid = np.isfinite(t).all(0) & np.isfinite(p).all(0) & (p >= 0).all(0)
    tann, tmin, tmax, pann = t.mean(0), t.min(0), t.max(0), p.sum(0)
    north_summer = p[3:9].sum(0)
    summer = np.where(lat[:, None] >= 0, north_summer, pann - north_summer)
    winter = pann - summer
    threshold = 20*tann + np.where(winter >= 2*pann/3, 0, np.where(summer >= 2*pann/3, 280, 140))
    result = np.where(tmin <= -3, 5, np.where(tmin < 18, 4, 1))
    result = np.where(pann <= threshold, 3, result)
    result = np.where(pann <= threshold/2, 2, result)
    result = np.where(tmax <= 10, 6, result)
    return np.where(valid, result, 0).astype('uint8')

def irradiation_classify(ghi, thresholds=(1130., 1560., 2070.)):
    if len(thresholds) != 3 or not np.all(np.diff(thresholds) > 0):
        raise ValueError("Three increasing irradiation thresholds required")
    g = np.asarray(ghi)
    return np.where(np.isfinite(g) & (g >= 0), np.digitize(g, thresholds, right=True)+1, 0).astype('uint8')

def combine(tp, irradiation):
    if np.shape(tp) != np.shape(irradiation):
        raise ValueError("Climate and irradiation grids must match")
    result = np.zeros_like(tp, dtype='uint8')
    raw = np.zeros_like(tp, dtype='uint8')
    for i, label in enumerate(TP_LABELS[1:], 1):
        for j in range(1, 5):
            selected = (tp == i) & (irradiation == j)
            result[selected] = ZONE_LABELS.index(MERGE[label][j-1])
            raw[selected] = (i-1)*4+j
    return result, raw
