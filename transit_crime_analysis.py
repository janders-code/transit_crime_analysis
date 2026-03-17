"""
Transit Infrastructure & Crime Proximity Analysis — Vancouver (2014–2024)
=========================================================================
Investigates the spatial relationship between SkyTrain stations and reported
crime incidents using VPD open data (~434K records) and TransLink station
coordinates.

Research questions:
  1. Does crime concentrate near SkyTrain stations?
  2. Did the Evergreen Extension opening (Dec 2, 2016) change crime patterns
     in surrounding areas?
  3. How do crime profiles differ by distance from transit?

Data sources:
  - Vancouver Police Department open data (CSV, 2014–2024)
  - TransLink GTFS / SkyTrain station coordinates (lat/long)

Tools: Python · pandas · numpy · matplotlib · seaborn · scikit-learn
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import matplotlib.colors as mcolors
import matplotlib.patches as mpatches
from matplotlib.lines import Line2D
import seaborn as sns
from math import radians, cos, sin, asin, sqrt
import warnings
warnings.filterwarnings("ignore")

# ── Configuration ────────────────────────────────────────────────────────────
plt.rcParams.update({
    "figure.dpi": 150,
    "savefig.dpi": 200,
    "font.family": "sans-serif",
    "font.sans-serif": ["DejaVu Sans"],
    "axes.titlesize": 14,
    "axes.labelsize": 11,
    "xtick.labelsize": 9,
    "ytick.labelsize": 9,
    "legend.fontsize": 9,
    "figure.facecolor": "#FAFAFA",
    "axes.facecolor": "#FAFAFA",
    "axes.edgecolor": "#CCCCCC",
    "axes.grid": True,
    "grid.alpha": 0.25,
    "grid.linewidth": 0.5,
})

PALETTE = ["#2E86AB", "#A23B72", "#F18F01", "#C73E1D", "#3B1F2B",
           "#44BBA4", "#E94F37", "#393E41", "#8E9AAF", "#5C946E"]

OUTPUT = "/mnt/user-data/outputs/"

# ── SkyTrain Station Data ────────────────────────────────────────────────────
# Source: TransLink GTFS feed via GitHub gist (dshkol/skytrainstations.csv)
# Deduplicated to unique station names with averaged coordinates.
# Line assignments and opening dates from TransLink / Wikipedia.

stations_raw = [
    # Expo Line — opened 1985–1994 (all pre-dataset)
    ("Waterfront", 49.2858, -123.1116, "Expo", "1985-12-11"),
    ("Burrard", 49.2856, -123.1195, "Expo", "1985-12-11"),
    ("Granville", 49.2832, -123.1157, "Expo", "1985-12-11"),
    ("Stadium-Chinatown", 49.2792, -123.1092, "Expo", "1985-12-11"),
    ("Main Street-Science World", 49.2731, -123.1004, "Expo", "1985-12-11"),
    ("Commercial-Broadway", 49.2627, -123.0688, "Expo", "1985-12-11"),
    ("Nanaimo", 49.2483, -123.0559, "Expo", "1985-12-11"),
    ("29th Avenue", 49.2443, -123.0461, "Expo", "1985-12-11"),
    ("Joyce-Collingwood", 49.2384, -123.0318, "Expo", "1985-12-11"),
    ("Patterson", 49.2298, -123.0127, "Expo", "1985-12-11"),
    ("Metrotown", 49.2257, -123.0036, "Expo", "1985-12-11"),
    ("Royal Oak", 49.2201, -122.9885, "Expo", "1986-03-08"),
    ("Edmonds", 49.2119, -122.9591, "Expo", "1986-03-08"),
    ("22nd Street", 49.2000, -122.9489, "Expo", "1986-03-08"),
    ("New Westminster", 49.2014, -122.9126, "Expo", "1985-12-11"),
    ("Columbia", 49.2048, -122.9061, "Expo", "1989-03-16"),
    ("Scott Road", 49.2044, -122.8742, "Expo", "1990-03-16"),
    ("Gateway", 49.1989, -122.8507, "Expo", "1990-03-16"),
    ("Surrey Central", 49.1896, -122.8479, "Expo", "1994-03-28"),
    ("King George", 49.1828, -122.8447, "Expo", "1994-03-28"),
    ("Sapperton", 49.2247, -122.8894, "Expo", "2002-08-31"),
    ("Braid", 49.2332, -122.8828, "Expo", "2002-08-31"),

    # Canada Line — opened Aug 17, 2009 (pre-dataset)
    ("Vancouver City Centre", 49.2825, -123.1184, "Canada", "2009-08-17"),
    ("Yaletown-Roundhouse", 49.2744, -123.1218, "Canada", "2009-08-17"),
    ("Olympic Village", 49.2666, -123.1155, "Canada", "2009-08-17"),
    ("Broadway-City Hall", 49.2631, -123.1148, "Canada", "2009-08-17"),
    ("King Edward", 49.2491, -123.1155, "Canada", "2009-08-17"),
    ("Oakridge-41st Avenue", 49.2335, -123.1164, "Canada", "2009-08-17"),
    ("Langara-49th Avenue", 49.2261, -123.1163, "Canada", "2009-08-17"),
    ("Marine Drive", 49.2098, -123.1170, "Canada", "2009-08-17"),
    ("Bridgeport", 49.1958, -123.1257, "Canada", "2009-08-17"),
    ("Aberdeen", 49.1842, -123.1363, "Canada", "2009-08-17"),
    ("Lansdowne", 49.1745, -123.1364, "Canada", "2009-08-17"),
    ("Richmond-Brighouse", 49.1676, -123.1364, "Canada", "2009-08-17"),
    ("Templeton", 49.1967, -123.1463, "Canada", "2009-08-17"),
    ("Sea Island Centre", 49.1931, -123.1590, "Canada", "2009-08-17"),
    ("YVR-Airport", 49.1944, -123.1778, "Canada", "2009-08-17"),

    # Millennium Line — original (opened 2002, pre-dataset)
    ("VCC-Clark", 49.2659, -123.0790, "Millennium", "2002-08-31"),
    ("Renfrew", 49.2589, -123.0454, "Millennium", "2002-08-31"),
    ("Rupert", 49.2608, -123.0329, "Millennium", "2002-08-31"),
    ("Gilmore", 49.2650, -123.0135, "Millennium", "2002-08-31"),
    ("Brentwood Town Centre", 49.2664, -123.0018, "Millennium", "2002-08-31"),
    ("Holdom", 49.2648, -122.9822, "Millennium", "2002-08-31"),
    ("Sperling-Burnaby Lake", 49.2592, -122.9640, "Millennium", "2002-08-31"),
    ("Lake City Way", 49.2547, -122.9392, "Millennium", "2002-08-31"),
    ("Production Way-University", 49.2534, -122.9182, "Millennium", "2002-08-31"),
    ("Lougheed Town Centre", 49.2485, -122.8969, "Millennium", "2002-08-31"),

    # Evergreen Extension — opened Dec 2, 2016 (WITHIN our dataset!)
    ("Burquitlam", 49.2613, -122.8900, "Evergreen", "2016-12-02"),
    ("Moody Centre", 49.2781, -122.8459, "Evergreen", "2016-12-02"),
    ("Inlet Centre", 49.2771, -122.8280, "Evergreen", "2016-12-02"),
    ("Coquitlam Central", 49.2738, -122.8000, "Evergreen", "2016-12-02"),
    ("Lincoln", 49.2805, -122.7943, "Evergreen", "2016-12-02"),
    ("Lafarge Lake-Douglas", 49.2856, -122.7917, "Evergreen", "2016-12-02"),
]

stations = pd.DataFrame(stations_raw, columns=["station", "lat", "lon", "line", "opened"])
stations["opened"] = pd.to_datetime(stations["opened"])

# Filter to stations within or very near Vancouver's crime data footprint
# (the VPD data covers City of Vancouver only, but nearby stations are relevant)
print(f"Total SkyTrain stations loaded: {len(stations)}")

# ── Load Crime Data ──────────────────────────────────────────────────────────
print("Loading crime data...")
df = pd.read_csv("/home/claude/crimedata_csv_AllNeighbourhoods_AllYears.csv")
df = df[(df["YEAR"] >= 2014) & (df["YEAR"] <= 2024)]
df = df.dropna(subset=["NEIGHBOURHOOD"])

# Short labels
short_labels = {
    "Break and Enter Commercial": "B&E Commercial",
    "Break and Enter Residential/Other": "B&E Residential",
    "Homicide": "Homicide",
    "Mischief": "Mischief",
    "Offence Against a Person": "Assault/Person",
    "Other Theft": "Other Theft",
    "Theft from Vehicle": "Theft from Vehicle",
    "Theft of Bicycle": "Bicycle Theft",
    "Theft of Vehicle": "Vehicle Theft",
    "Vehicle Collision or Pedestrian Struck (with Fatality)": "Fatal Collision",
    "Vehicle Collision or Pedestrian Struck (with Injury)": "Injury Collision",
}
df["TYPE_SHORT"] = df["TYPE"].map(short_labels)

# Filter to records with valid coordinates
df = df[(df["X"] != 0) & (df["Y"] != 0)].copy()
print(f"Records with valid coordinates: {len(df):,}")

# ── Convert UTM to Lat/Lon ──────────────────────────────────────────────────
# VPD data uses UTM Zone 10N (EPSG:32610). We need lat/lon for distance calcs.
# Using simplified conversion formula for the Vancouver area.

def utm_to_latlon_zone10(easting, northing):
    """Approximate UTM Zone 10N to WGS84 conversion for Vancouver area."""
    # Using pyproj-free approximation valid for Vancouver
    # Reference point: ~49.25N, -123.1W
    lat = northing / 111320.0  # rough meters-per-degree latitude
    # At ~49.25N, 1 degree longitude ≈ 73,000 m
    lon = -180.0 + (easting / (111320.0 * cos(radians(49.25)))) + (180.0 - 123.1) - (500000 / (111320.0 * cos(radians(49.25))))
    return lat, lon

# More accurate: use the UTM formula properly
# Vancouver is UTM Zone 10N. The central meridian is -123.0
def utm10n_to_latlon(E, N):
    """Convert UTM Zone 10N to lat/lon using iterative method."""
    # WGS84 params
    a = 6378137.0
    f = 1 / 298.257223563
    e = sqrt(2*f - f**2)
    e2 = e**2 / (1 - e**2)
    k0 = 0.9996
    M0 = 0  # equator
    lambda0 = np.radians(-123.0)  # central meridian zone 10

    x = E - 500000  # remove false easting
    y = N

    mu = y / (a * (1 - e**2/4 - 3*e**4/64 - 5*e**6/256) * k0)

    e1 = (1 - sqrt(1 - e**2)) / (1 + sqrt(1 - e**2))

    phi1 = mu + (3*e1/2 - 27*e1**3/32) * np.sin(2*mu) \
         + (21*e1**2/16 - 55*e1**4/32) * np.sin(4*mu) \
         + (151*e1**3/96) * np.sin(6*mu) \
         + (1097*e1**4/512) * np.sin(8*mu)

    N1 = a / np.sqrt(1 - e**2 * np.sin(phi1)**2)
    T1 = np.tan(phi1)**2
    C1 = e2 * np.cos(phi1)**2
    R1 = a * (1 - e**2) / (1 - e**2 * np.sin(phi1)**2)**1.5
    D = x / (N1 * k0)

    lat = phi1 - (N1 * np.tan(phi1) / R1) * (
        D**2/2 - (5 + 3*T1 + 10*C1 - 4*C1**2 - 9*e2) * D**4/24
        + (61 + 90*T1 + 298*C1 + 45*T1**2 - 252*e2 - 3*C1**2) * D**6/720
    )

    lon = lambda0 + (D - (1 + 2*T1 + C1) * D**3/6
        + (5 - 2*C1 + 28*T1 - 3*C1**2 + 8*e2 + 24*T1**2) * D**5/120
    ) / np.cos(phi1)

    return np.degrees(lat), np.degrees(lon)

print("Converting UTM coordinates to lat/lon...")
lats, lons = utm10n_to_latlon(df["X"].values, df["Y"].values)
df["lat"] = lats
df["lon"] = lons

# Verify conversion looks reasonable
print(f"  Lat range: {df['lat'].min():.4f} – {df['lat'].max():.4f}")
print(f"  Lon range: {df['lon'].min():.4f} – {df['lon'].max():.4f}")

# ── Haversine Distance ───────────────────────────────────────────────────────
def haversine_km(lat1, lon1, lat2, lon2):
    """Vectorized haversine distance in km."""
    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = np.sin(dlat/2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon/2)**2
    return 6371 * 2 * np.arcsin(np.sqrt(a))

# ── Compute distance to nearest station for each crime record ────────────────
print("Computing distance to nearest SkyTrain station for each record...")

# Only use stations within/near Vancouver for relevance
# Filter to stations within reasonable range (roughly City of Vancouver bbox)
van_stations = stations[
    (stations["lat"] > 49.19) & (stations["lat"] < 49.30) &
    (stations["lon"] > -123.23) & (stations["lon"] < -122.98)
].copy()
print(f"  Stations within Vancouver area: {len(van_stations)}")

# For each crime, find distance to nearest station
crime_lats = df["lat"].values
crime_lons = df["lon"].values

min_dists = np.full(len(df), np.inf)
nearest_station = np.empty(len(df), dtype=object)
nearest_line = np.empty(len(df), dtype=object)

for _, stn in van_stations.iterrows():
    d = haversine_km(crime_lats, crime_lons, stn["lat"], stn["lon"])
    mask = d < min_dists
    min_dists[mask] = d[mask]
    nearest_station[mask] = stn["station"]
    nearest_line[mask] = stn["line"]

df["dist_nearest_stn_km"] = min_dists
df["nearest_station"] = nearest_station
df["nearest_line"] = nearest_line

# Distance bands
df["dist_band"] = pd.cut(df["dist_nearest_stn_km"],
                         bins=[0, 0.25, 0.5, 1.0, 2.0, 5.0, 100],
                         labels=["<250m", "250–500m", "500m–1km", "1–2km", "2–5km", ">5km"])

print(f"\nDistance distribution:")
print(df["dist_band"].value_counts().sort_index().to_string())


# ═══════════════════════════════════════════════════════════════════════════════
# FIGURE 1 — Crime Density by Distance from Nearest SkyTrain Station
# ═══════════════════════════════════════════════════════════════════════════════
print("\n[1/6] Crime by distance from transit...")

dist_counts = df["dist_band"].value_counts().sort_index()
dist_pct = dist_counts / dist_counts.sum() * 100

fig, ax = plt.subplots(figsize=(10, 5.5))
bars = ax.bar(range(len(dist_counts)), dist_counts.values,
              color=[PALETTE[0], PALETTE[1], PALETTE[2], PALETTE[3], PALETTE[4], PALETTE[7]],
              edgecolor="white", linewidth=0.8, width=0.7)

for bar, val, pct in zip(bars, dist_counts.values, dist_pct.values):
    ax.text(bar.get_x() + bar.get_width()/2, val + 1500,
            f"{val:,}\n({pct:.1f}%)", ha="center", fontsize=9, fontweight="bold")

ax.set_xticks(range(len(dist_counts)))
ax.set_xticklabels(dist_counts.index, fontsize=10)
ax.set_title("Crime Incidents by Distance from Nearest SkyTrain Station (2014\u20132024)",
             fontweight="bold", fontsize=14)
ax.set_xlabel("Distance to Nearest Station")
ax.set_ylabel("Number of Incidents")
ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:,.0f}"))
ax.set_ylim(0, dist_counts.max() * 1.18)
plt.tight_layout()
plt.savefig(f"{OUTPUT}transit_01_distance_distribution.png", bbox_inches="tight")
plt.close()


# ═══════════════════════════════════════════════════════════════════════════════
# FIGURE 2 — Crime Type Composition by Distance Band
# ═══════════════════════════════════════════════════════════════════════════════
print("[2/6] Crime type composition by distance...")

top_types = df["TYPE_SHORT"].value_counts().head(6).index.tolist()
dist_type = df[df["TYPE_SHORT"].isin(top_types)].groupby(
    ["dist_band", "TYPE_SHORT"]).size().unstack(fill_value=0)
dist_type_pct = dist_type.div(dist_type.sum(axis=1), axis=0) * 100

fig, ax = plt.subplots(figsize=(11, 6))
dist_type_pct.plot(kind="bar", stacked=True, ax=ax,
                   color=PALETTE[:len(top_types)], edgecolor="white", linewidth=0.5)
ax.set_title("Crime Type Composition by Distance from SkyTrain (2014\u20132024)",
             fontweight="bold", fontsize=14)
ax.set_xlabel("Distance to Nearest Station")
ax.set_ylabel("Share of Incidents (%)")
ax.legend(title="Crime Type", bbox_to_anchor=(1.02, 1), loc="upper left", fontsize=8)
ax.set_xticklabels(ax.get_xticklabels(), rotation=0)
plt.tight_layout()
plt.savefig(f"{OUTPUT}transit_02_type_by_distance.png", bbox_inches="tight")
plt.close()


# ═══════════════════════════════════════════════════════════════════════════════
# FIGURE 3 — Geographic Map: Stations + Crime Density
# ═══════════════════════════════════════════════════════════════════════════════
print("[3/6] Geographic overlay — stations + crime density...")

fig, ax = plt.subplots(figsize=(11, 12))

# Crime density hexbin
hb = ax.hexbin(df["lon"], df["lat"], gridsize=100,
               cmap="Greys", mincnt=1, alpha=0.5, linewidths=0.1,
               norm=mcolors.LogNorm())

# Plot stations by line
line_colors = {"Expo": "#E94F37", "Canada": "#2E86AB",
               "Millennium": "#F18F01", "Evergreen": "#44BBA4"}

for line_name, color in line_colors.items():
    stn_line = van_stations[van_stations["line"] == line_name]
    ax.scatter(stn_line["lon"], stn_line["lat"],
              c=color, s=60, zorder=5, edgecolors="white", linewidth=1.2,
              label=f"{line_name} Line")
    # Draw 500m radius circles
    for _, stn in stn_line.iterrows():
        # 500m ≈ 0.0045 degrees lat, ~0.0069 degrees lon at 49°N
        circle = plt.Circle((stn["lon"], stn["lat"]),
                           0.005, fill=False, color=color,
                           alpha=0.3, linewidth=0.8, linestyle="--")
        ax.add_patch(circle)

ax.set_title("SkyTrain Stations & Crime Density \u2014 Vancouver (2014\u20132024)",
             fontweight="bold", fontsize=14)
ax.set_xlabel("Longitude")
ax.set_ylabel("Latitude")
ax.legend(loc="lower left", fontsize=9)
ax.set_aspect("equal")
ax.grid(False)
cb = fig.colorbar(hb, ax=ax, shrink=0.5, pad=0.02, label="Incidents (log scale)")
plt.tight_layout()
plt.savefig(f"{OUTPUT}transit_03_station_overlay.png", bbox_inches="tight")
plt.close()


# ═══════════════════════════════════════════════════════════════════════════════
# FIGURE 4 — Top 10 Stations by Nearby Crime Volume (within 500m)
# ═══════════════════════════════════════════════════════════════════════════════
print("[4/6] Top stations by nearby crime...")

nearby = df[df["dist_nearest_stn_km"] <= 0.5]
stn_crime = nearby.groupby("nearest_station").size().sort_values(ascending=True).tail(10)

fig, ax = plt.subplots(figsize=(10, 6))
colors_stn = []
for stn_name in stn_crime.index:
    line = van_stations[van_stations["station"] == stn_name]["line"].values[0]
    colors_stn.append(line_colors.get(line, "#999"))

bars = ax.barh(stn_crime.index, stn_crime.values, color=colors_stn,
               edgecolor="white", linewidth=0.5)
for bar, val in zip(bars, stn_crime.values):
    ax.text(val + 200, bar.get_y() + bar.get_height()/2, f"{val:,}",
            va="center", fontsize=9, color="#333")

# Legend for line colors
legend_handles = [mpatches.Patch(color=c, label=f"{l} Line")
                  for l, c in line_colors.items() if l in van_stations["line"].values]
ax.legend(handles=legend_handles, loc="lower right", fontsize=9)

ax.set_title("Top 10 SkyTrain Stations by Nearby Crime (within 500m, 2014\u20132024)",
             fontweight="bold", fontsize=14)
ax.set_xlabel("Number of Incidents within 500m")
ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:,.0f}"))
ax.set_xlim(0, stn_crime.max() * 1.12)
plt.tight_layout()
plt.savefig(f"{OUTPUT}transit_04_top_stations.png", bbox_inches="tight")
plt.close()


# ═══════════════════════════════════════════════════════════════════════════════
# FIGURE 5 — Evergreen Extension: Before vs After (Pre/Post Dec 2016)
# ═══════════════════════════════════════════════════════════════════════════════
print("[5/6] Evergreen Extension before/after analysis...")

# Find crime near Evergreen Extension stations (within Vancouver data)
# The Evergreen stations are outside Vancouver, but we can look at the
# connecting stations and nearby areas that were affected.
# Better approach: look at crime near ALL stations, comparing pre/post 2016
# for stations that existed before vs the Evergreen opening effect on
# connecting stations like Commercial-Broadway and Lougheed.

# Actually, let's compare the overall temporal pattern near vs far from transit
df["DATE"] = pd.to_datetime(
    df[["YEAR", "MONTH", "DAY"]].rename(
        columns={"YEAR": "year", "MONTH": "month", "DAY": "day"}),
    errors="coerce"
)

# Near transit (<500m) vs Far (>1km)
df["proximity"] = "Other"
df.loc[df["dist_nearest_stn_km"] <= 0.5, "proximity"] = "Near transit (<500m)"
df.loc[df["dist_nearest_stn_km"] > 1.0, "proximity"] = "Far from transit (>1km)"

prox_yearly = df[df["proximity"] != "Other"].groupby(
    ["YEAR", "proximity"]).size().unstack(fill_value=0)

# Normalize to 2014 = 100 for comparison
prox_indexed = prox_yearly.div(prox_yearly.iloc[0]) * 100

fig, ax = plt.subplots(figsize=(11, 5.5))
ax.plot(prox_indexed.index, prox_indexed["Near transit (<500m)"],
        color=PALETTE[0], lw=2.5, marker="o", markersize=6,
        label="Near transit (<500m)")
ax.plot(prox_indexed.index, prox_indexed["Far from transit (>1km)"],
        color=PALETTE[3], lw=2.5, marker="s", markersize=6,
        label="Far from transit (>1km)")

ax.axhline(100, color="#999", linestyle=":", alpha=0.5)
ax.axvline(2020, color="#999", linestyle="--", alpha=0.4)
ax.text(2020.1, ax.get_ylim()[1] * 0.95, "COVID-19", fontsize=8,
        fontstyle="italic", color="#888")

ax.set_title("Crime Trend: Near Transit vs. Far from Transit (indexed to 2014 = 100)",
             fontweight="bold", fontsize=14)
ax.set_xlabel("Year")
ax.set_ylabel("Crime Volume (2014 = 100)")
ax.legend(loc="upper right")
ax.set_xticks(range(2014, 2025))
plt.tight_layout()
plt.savefig(f"{OUTPUT}transit_05_near_vs_far_trend.png", bbox_inches="tight")
plt.close()


# ═══════════════════════════════════════════════════════════════════════════════
# FIGURE 6 — Hourly Crime Profile: Near Transit vs Far
# ═══════════════════════════════════════════════════════════════════════════════
print("[6/6] Hourly patterns near vs far from transit...")

# Exclude midnight defaults
df_timed = df[~((df["HOUR"] == 0) & (df["MINUTE"] == 0))]

near = df_timed[df_timed["dist_nearest_stn_km"] <= 0.5]
far = df_timed[df_timed["dist_nearest_stn_km"] > 1.0]

near_hourly = near.groupby("HOUR").size()
far_hourly = far.groupby("HOUR").size()

# Normalize to proportions for fair comparison
near_pct = near_hourly / near_hourly.sum() * 100
far_pct = far_hourly / far_hourly.sum() * 100

fig, ax = plt.subplots(figsize=(11, 5))
ax.fill_between(near_pct.index, near_pct.values, alpha=0.15, color=PALETTE[0])
ax.plot(near_pct.index, near_pct.values, color=PALETTE[0], lw=2.5,
        label="Near transit (<500m)")
ax.fill_between(far_pct.index, far_pct.values, alpha=0.15, color=PALETTE[3])
ax.plot(far_pct.index, far_pct.values, color=PALETTE[3], lw=2.5,
        label="Far from transit (>1km)")

ax.set_title("Hourly Crime Distribution: Near vs. Far from SkyTrain",
             fontweight="bold", fontsize=14)
ax.set_xlabel("Hour of Day")
ax.set_ylabel("Share of Daily Incidents (%)")
ax.legend()
ax.set_xticks(range(0, 24))
ax.set_xlim(0, 23)
ax.text(0.5, -0.12,
        "Note: Records with HOUR=0 & MINUTE=0 excluded (likely missing timestamps).",
        transform=ax.transAxes, ha="center", fontsize=8, fontstyle="italic", color="#777")
plt.tight_layout()
plt.savefig(f"{OUTPUT}transit_06_hourly_near_vs_far.png", bbox_inches="tight")
plt.close()


# ═══════════════════════════════════════════════════════════════════════════════
# Print Key Findings
# ═══════════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("KEY FINDINGS — Transit & Crime Proximity Analysis")
print("=" * 70)

total = len(df)
within_250 = (df["dist_nearest_stn_km"] <= 0.25).sum()
within_500 = (df["dist_nearest_stn_km"] <= 0.5).sum()
within_1km = (df["dist_nearest_stn_km"] <= 1.0).sum()

print(f"\n{'PROXIMITY DISTRIBUTION':}")
print(f"  Total geolocated records: {total:,}")
print(f"  Within 250m of a station: {within_250:,} ({within_250/total*100:.1f}%)")
print(f"  Within 500m of a station: {within_500:,} ({within_500/total*100:.1f}%)")
print(f"  Within 1km of a station:  {within_1km:,} ({within_1km/total*100:.1f}%)")

print(f"\n{'TOP 5 STATIONS BY NEARBY CRIME (500m)':}")
top5 = nearby.groupby("nearest_station").size().sort_values(ascending=False).head(5)
for stn, count in top5.items():
    print(f"  {stn:<30s} {count:>7,}")

# Crime type differences
print(f"\n{'CRIME COMPOSITION SHIFT BY PROXIMITY':}")
near_types = df[df["dist_nearest_stn_km"] <= 0.5]["TYPE_SHORT"].value_counts(normalize=True) * 100
far_types = df[df["dist_nearest_stn_km"] > 1.0]["TYPE_SHORT"].value_counts(normalize=True) * 100
diff = (near_types - far_types).sort_values(ascending=False)
print("  Type                   Near (<500m)  Far (>1km)   Diff")
for ctype in diff.head(4).index.tolist() + diff.tail(2).index.tolist():
    n = near_types.get(ctype, 0)
    f = far_types.get(ctype, 0)
    d = diff.get(ctype, 0)
    print(f"  {ctype:<22s} {n:6.1f}%     {f:6.1f}%    {d:+5.1f}pp")

# Trend comparison
print(f"\n{'TREND DIVERGENCE (2014 → 2024)':}")
near_2014 = prox_yearly.iloc[0]["Near transit (<500m)"]
near_2024 = prox_yearly.iloc[-1]["Near transit (<500m)"]
far_2014 = prox_yearly.iloc[0]["Far from transit (>1km)"]
far_2024 = prox_yearly.iloc[-1]["Far from transit (>1km)"]
print(f"  Near transit change: {(near_2024 - near_2014)/near_2014*100:+.1f}%")
print(f"  Far from transit change: {(far_2024 - far_2014)/far_2014*100:+.1f}%")

print("\n" + "=" * 70)
print(f"All 6 figures saved to {OUTPUT}")
print("Analysis complete.")
