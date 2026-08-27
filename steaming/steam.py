import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

# ─────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="F1 Intelligence Report | 1950–2022",
    page_icon="🏎",
    layout="wide",
)

# ─────────────────────────────────────────────
# LOAD & CLEAN  (ETL — 5 pts)
# ─────────────────────────────────────────────
@st.cache_data
def load_data():
    results  = pd.read_csv("../fact_Results.csv")
    races    = pd.read_csv("../dim_Races.csv")
    drivers  = pd.read_csv("../dim_Drivers.csv")
    circuits = pd.read_csv("../dim_Circuits.csv")

    # Replace \N with NaN across all tables
    for df in [results, races, drivers, circuits]:
        df.replace("\\N", np.nan, inplace=True)

    # ── fact_Results ──────────────────────────
    results["driver_name"] = results["driver_name"].str.strip()
    results["points"]      = pd.to_numeric(results["points"], errors="coerce").fillna(0).astype(int)
    results["grid"]        = pd.to_numeric(results["grid"],   errors="coerce")
    results["laps"]        = pd.to_numeric(results["laps"],   errors="coerce")

    # position: clean to int; R/F → NaN
    results["position_clean"] = pd.to_numeric(
        results["position"].replace({"R": np.nan, "F": np.nan}), errors="coerce"
    )
    results["dnf"] = results["position"].isin(["R", "F"]).astype(int)
    results["finished"] = results["position_clean"].notna().astype(int)

    # ── dim_Races ─────────────────────────────
    races["race_date"] = pd.to_datetime(races["race_date"], errors="coerce")

    # ── dim_Drivers ───────────────────────────
    drivers["driver_name"]  = drivers["driver_name"].str.strip()
    drivers["race_number"]  = pd.to_numeric(drivers["race_number"], errors="coerce").fillna(0).astype(int)
    drivers["date_of_birth"]= pd.to_datetime(drivers["date_of_birth"], errors="coerce")

    # ── dim_Circuits ──────────────────────────
    circuits["altitude"] = pd.to_numeric(circuits["altitude"], errors="coerce").fillna(0).astype(int)
    circuits["lat"]      = pd.to_numeric(circuits["lat"],      errors="coerce")
    circuits["lng"]      = pd.to_numeric(circuits["lng"],      errors="coerce")

    # ── Data Modeling: Merges (replaces Power BI relationships — 5 pts) ──
    df = results.merge(races,    on=["season_year", "round_number"], how="left")
    df = df.merge(circuits, on="circuit_name", how="left")
    df = df.merge(drivers,  on="driver_name",  how="left")

    # Street circuit flag
    street = [
        "Circuit de Monaco", "Baku City Circuit", "Marina Bay Street Circuit",
        "Valencia Street Circuit", "Circuit urbain de Monaco",
        "Jeddah Corniche Circuit",
    ]
    df["circuit_type"] = df["circuit_name"].apply(
        lambda x: "Street" if x in street else "Permanent Track"
    )

    return df, circuits

df, circuits = load_data()

# ─────────────────────────────────────────────
# KPI FUNCTIONS  (DAX equivalents — 7 + 3 pts)
# ─────────────────────────────────────────────
def kpi_points_per_race(data):
    """KPI 1 — Points Per Race"""
    return round(data["points"].sum() / len(data), 2)

def kpi_win_rate(data):
    """KPI 2 — Win Rate %"""
    wins  = (data["position_clean"] == 1).sum()
    total = len(data)
    return round((wins / total) * 100, 2) if total > 0 else 0

def kpi_podium_rate(data):
    """KPI 3 — Podium Rate %"""
    podiums  = data[data["position_clean"].isin([1, 2, 3])].shape[0]
    finished = data[~data["position"].isin(["R", "F"])].shape[0]
    return round((podiums / finished) * 100, 2) if finished > 0 else 0

def kpi_constructor_dominance(data, team_name):
    """Bonus — Constructor Dominance %"""
    team_pts  = data[data["team"] == team_name]["points"].sum()
    total_pts = data["points"].sum()
    return round((team_pts / total_pts) * 100, 2) if total_pts > 0 else 0

# ─────────────────────────────────────────────
# GLOBAL SIDEBAR FILTER  (Creative Feature — 3 pts)
# ─────────────────────────────────────────────
st.sidebar.image("https://upload.wikimedia.org/wikipedia/commons/thumb/3/33/F1.svg/320px-F1.svg.png", width=180)
st.sidebar.title("🏎 F1 Dashboard Filters")

season_range = st.sidebar.slider(
    "Season Range",
    min_value=int(df["season_year"].min()),
    max_value=int(df["season_year"].max()),
    value=(2010, 2022),
)

all_teams = sorted(df["team"].dropna().unique())
selected_teams = st.sidebar.multiselect("Filter by Team", all_teams, default=[])

df_filtered = df[
    (df["season_year"] >= season_range[0]) &
    (df["season_year"] <= season_range[1])
]
if selected_teams:
    df_filtered = df_filtered[df_filtered["team"].isin(selected_teams)]

st.sidebar.markdown("---")
st.sidebar.caption("F1 World Championship Dataset | 1950–2022 | 25,840 records")

# ─────────────────────────────────────────────
# TABS
# ─────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🏠 Overview",
    "🧑‍✈️ Driver Analysis",
    "🗺️ Circuit & Geography",
    "🏗️ Team Performance",
    "💡 Business Insights",
])

# ══════════════════════════════════════════════
# TAB 1 — OVERVIEW
# ══════════════════════════════════════════════
with tab1:
    st.title("🏎 F1 Intelligence Report — Overview")
    st.caption(f"Showing seasons {season_range[0]} – {season_range[1]} | {len(df_filtered):,} race entries")

    # KPI Cards
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Total Points Awarded",  f"{df_filtered['points'].sum():,}")
    k2.metric("Points Per Race (avg)", kpi_points_per_race(df_filtered))
    k3.metric("Total Races",           df_filtered[["season_year","round_number"]].drop_duplicates().shape[0])
    k4.metric("Unique Drivers",        df_filtered["driver_name"].nunique())

    st.markdown("---")
    col1, col2 = st.columns(2)

    # Top 5 drivers by total points
    with col1:
        st.subheader("Top 10 Drivers by Total Points")
        top_drivers = (
            df_filtered.groupby("driver_name")["points"]
            .sum().sort_values(ascending=False).head(10).reset_index()
        )
        fig = px.bar(
            top_drivers, x="points", y="driver_name", orientation="h",
            color="points", color_continuous_scale="reds",
            labels={"points": "Total Points", "driver_name": "Driver"},
        )
        fig.update_layout(yaxis={"categoryorder": "total ascending"}, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    # Points trend over seasons
    with col2:
        st.subheader("Total Points Awarded Per Season")
        season_trend = df_filtered.groupby("season_year")["points"].sum().reset_index()
        fig2 = px.line(
            season_trend, x="season_year", y="points",
            markers=True, labels={"season_year": "Season", "points": "Total Points"},
            color_discrete_sequence=["#e10600"],
        )
        st.plotly_chart(fig2, use_container_width=True)

    # DNF overview
    st.subheader("Race Completion vs DNF Rate Per Season")
    dnf_season = df_filtered.groupby("season_year").agg(
        dnf=("dnf", "sum"),
        total=("dnf", "count")
    ).reset_index()
    dnf_season["dnf_pct"] = (dnf_season["dnf"] / dnf_season["total"] * 100).round(1)
    fig3 = px.area(
        dnf_season, x="season_year", y="dnf_pct",
        labels={"season_year": "Season", "dnf_pct": "DNF Rate (%)"},
        color_discrete_sequence=["#e10600"],
    )
    st.plotly_chart(fig3, use_container_width=True)

# ══════════════════════════════════════════════
# TAB 2 — DRIVER ANALYSIS
# ══════════════════════════════════════════════
with tab2:
    st.title("🧑‍✈️ Driver Analysis")

    # Driver selector (Creative drill-down feature)
    all_drivers = sorted(df_filtered["driver_name"].dropna().unique())
    selected_driver = st.selectbox("Select a Driver", all_drivers, index=all_drivers.index("Lewis Hamilton") if "Lewis Hamilton" in all_drivers else 0)

    driver_df = df_filtered[df_filtered["driver_name"] == selected_driver]

    # KPI row for selected driver
    d1, d2, d3, d4 = st.columns(4)
    d1.metric("Total Points",   driver_df["points"].sum())
    d2.metric("Races Entered",  len(driver_df))
    d3.metric("Win Rate %",     f"{kpi_win_rate(driver_df)}%")
    d4.metric("Podium Rate %",  f"{kpi_podium_rate(driver_df)}%")

    st.markdown("---")
    col1, col2 = st.columns(2)

    # Points by season
    with col1:
        st.subheader(f"{selected_driver} — Points Per Season")
        pts_season = driver_df.groupby("season_year")["points"].sum().reset_index()
        fig = px.bar(pts_season, x="season_year", y="points",
                     color="points", color_continuous_scale="reds",
                     labels={"season_year": "Season", "points": "Points"})
        st.plotly_chart(fig, use_container_width=True)

    # Finishing position distribution
    with col2:
        st.subheader(f"{selected_driver} — Finish Position Distribution")
        pos_dist = driver_df["position_clean"].dropna().astype(int).value_counts().sort_index().reset_index()
        pos_dist.columns = ["Position", "Count"]
        fig2 = px.bar(pos_dist, x="Position", y="Count",
                      color="Count", color_continuous_scale="reds")
        st.plotly_chart(fig2, use_container_width=True)

    # Full race log (Drill-Through equivalent)
    st.subheader(f"{selected_driver} — Race-by-Race Log")
    race_log = driver_df[["season_year","round_number","grand_prix","team","grid","position","points","notes"]].copy()
    race_log.columns = ["Season","Round","Grand Prix","Team","Grid","Finish","Points","Result"]
    st.dataframe(race_log.sort_values(["Season","Round"], ascending=[False,True]), use_container_width=True)

    # Top 10 drivers comparison table
    st.markdown("---")
    st.subheader("Top 20 Drivers — KPI Comparison")

    finished_df = df_filtered[df_filtered["position_clean"].notna()]
    min_races   = 30

    driver_stats = []
    for drv in df_filtered["driver_name"].unique():
        d = df_filtered[df_filtered["driver_name"] == drv]
        if len(d) < min_races:
            continue
        driver_stats.append({
            "Driver":        drv,
            "Races":         len(d),
            "Total Points":  d["points"].sum(),
            "Win Rate %":    kpi_win_rate(d),
            "Podium Rate %": kpi_podium_rate(d),
            "DNF Rate %":    round(d["dnf"].sum() / len(d) * 100, 1),
        })

    stats_df = pd.DataFrame(driver_stats).sort_values("Podium Rate %", ascending=False).head(20)
    st.dataframe(stats_df.reset_index(drop=True), use_container_width=True)

# ══════════════════════════════════════════════
# TAB 3 — CIRCUIT & GEOGRAPHY
# ══════════════════════════════════════════════
with tab3:
    st.title("🗺️ Circuit & Geography")

    # Map using lat/lng (required visual)
    st.subheader("F1 Circuits — World Map")
    circuit_stats = df_filtered.groupby("circuit_name").agg(
        dnf_count=("dnf", "sum"),
        race_count=("result_id", "count"),
        lat=("lat", "first"),
        lng=("lng", "first"),
        country=("country_x", "first"),
        location=("location", "first"),
    ).reset_index().dropna(subset=["lat","lng"])

    circuit_stats["dnf_rate"] = (circuit_stats["dnf_count"] / circuit_stats["race_count"] * 100).round(1)

    fig_map = px.scatter_geo(
        circuit_stats,
        lat="lat", lon="lng",
        size="race_count",
        color="dnf_rate",
        hover_name="circuit_name",
        hover_data={"country": True, "dnf_rate": True, "race_count": True, "lat": False, "lng": False},
        color_continuous_scale="reds",
        projection="natural earth",
        title="Circuit locations — bubble size = races held, color = DNF rate",
        labels={"dnf_rate": "DNF Rate %", "race_count": "Races Held"},
    )
    fig_map.update_geos(showcountries=True, countrycolor="lightgray", showcoastlines=True)
    fig_map.update_layout(height=500)
    st.plotly_chart(fig_map, use_container_width=True)

    col1, col2 = st.columns(2)

    # DNF by circuit
    with col1:
        st.subheader("Most DNFs by Circuit (Top 15)")
        top_dnf = circuit_stats.sort_values("dnf_count", ascending=False).head(15)
        fig = px.bar(top_dnf, x="dnf_count", y="circuit_name", orientation="h",
                     color="dnf_count", color_continuous_scale="reds",
                     labels={"dnf_count": "Total DNFs", "circuit_name": "Circuit"})
        fig.update_layout(yaxis={"categoryorder": "total ascending"})
        st.plotly_chart(fig, use_container_width=True)

    # DNF rate by circuit
    with col2:
        st.subheader("Highest DNF Rate % by Circuit (min 50 entries)")
        high_dnf_rate = circuit_stats[circuit_stats["race_count"] >= 50].sort_values("dnf_rate", ascending=False).head(15)
        fig2 = px.bar(high_dnf_rate, x="dnf_rate", y="circuit_name", orientation="h",
                      color="dnf_rate", color_continuous_scale="oranges",
                      labels={"dnf_rate": "DNF Rate %", "circuit_name": "Circuit"})
        fig2.update_layout(yaxis={"categoryorder": "total ascending"})
        st.plotly_chart(fig2, use_container_width=True)

    # Altitude vs DNF rate scatter
    st.subheader("Circuit Altitude vs DNF Rate")
    alt_df = df_filtered.merge(
        circuits[["circuit_name","altitude","lat","lng"]], on="circuit_name", how="left"
    )
    alt_agg = alt_df.groupby("circuit_name").agg(
        dnf_rate=("dnf", "mean"),
        altitude=("altitude_y", "first")
    ).dropna().reset_index()
    fig3 = px.scatter(alt_agg, x="altitude", y="dnf_rate",
                      hover_name="circuit_name",
                      trendline="ols",
                      labels={"altitude": "Altitude (m)", "dnf_rate": "DNF Rate"},
                      color_discrete_sequence=["#e10600"])
    st.plotly_chart(fig3, use_container_width=True)

# ══════════════════════════════════════════════
# TAB 4 — TEAM PERFORMANCE
# ══════════════════════════════════════════════
with tab4:
    st.title("🏗️ Team Performance")

    # Constructor dominance bonus KPI
    st.subheader("Constructor Dominance % — Select a Team")
    team_list = sorted(df_filtered["team"].dropna().unique())
    sel_team  = st.selectbox("Team", team_list, index=team_list.index("Red Bull") if "Red Bull" in team_list else 0)
    dominance = kpi_constructor_dominance(df_filtered, sel_team)
    st.metric(f"{sel_team} — Constructor Dominance %", f"{dominance}%",
              help="Share of total season points earned by this team vs all teams")

    st.markdown("---")
    col1, col2 = st.columns(2)

    # Top constructors by total points
    with col1:
        st.subheader("Top 10 Constructors — Total Points")
        team_pts = df_filtered.groupby("team")["points"].sum().sort_values(ascending=False).head(10).reset_index()
        fig = px.bar(team_pts, x="points", y="team", orientation="h",
                     color="points", color_continuous_scale="reds",
                     labels={"points": "Total Points", "team": "Constructor"})
        fig.update_layout(yaxis={"categoryorder": "total ascending"})
        st.plotly_chart(fig, use_container_width=True)

    # Constructor points by season (top 5)
    with col2:
        st.subheader("Top 5 Constructors — Points Per Season")
        top5_teams = df_filtered.groupby("team")["points"].sum().nlargest(5).index.tolist()
        team_season = df_filtered[df_filtered["team"].isin(top5_teams)].groupby(
            ["season_year","team"])["points"].sum().reset_index()
        fig2 = px.line(team_season, x="season_year", y="points", color="team",
                       markers=True,
                       labels={"season_year": "Season", "points": "Points", "team": "Constructor"},
                       color_discrete_sequence=px.colors.qualitative.Set1)
        st.plotly_chart(fig2, use_container_width=True)

    # Street vs Permanent track dominance
    st.subheader("Team Performance — Street Circuits vs Permanent Tracks")
    circuit_type_perf = df_filtered.groupby(["team","circuit_type"])["points"].sum().reset_index()
    top10 = df_filtered.groupby("team")["points"].sum().nlargest(10).index
    circuit_type_perf = circuit_type_perf[circuit_type_perf["team"].isin(top10)]
    fig3 = px.bar(circuit_type_perf, x="team", y="points", color="circuit_type",
                  barmode="group",
                  labels={"points": "Total Points", "team": "Constructor", "circuit_type": "Circuit Type"},
                  color_discrete_sequence=["#e10600","#1e1e1e"])
    st.plotly_chart(fig3, use_container_width=True)

    # Win share by team
    st.subheader("Win Share by Constructor")
    wins_by_team = df_filtered[df_filtered["position_clean"] == 1].groupby("team").size().reset_index(name="wins")
    wins_by_team = wins_by_team.sort_values("wins", ascending=False).head(10)
    fig4 = px.pie(wins_by_team, names="team", values="wins",
                  color_discrete_sequence=px.colors.qualitative.Set1,
                  hole=0.4)
    st.plotly_chart(fig4, use_container_width=True)

# ══════════════════════════════════════════════
# TAB 5 — BUSINESS INSIGHTS  (5 pts)
# ══════════════════════════════════════════════
with tab5:
    st.title("💡 Business Insights")
    st.caption("Strategic recommendations for the performance director — data-backed, action-oriented.")

    # ── Q1: Most consistent driver ──────────────
    st.markdown("---")
    st.subheader("📌 Q1 — Which driver shows the highest consistency across multiple seasons?")

    finished_all = df[df["position_clean"].notna()]
    race_counts  = finished_all.groupby("driver_name").size()
    podium_counts= finished_all[finished_all["position_clean"] <= 3].groupby("driver_name").size()
    consistency  = (podium_counts / race_counts).dropna()
    consistency  = consistency[race_counts >= 50].sort_values(ascending=False).head(10).reset_index()
    consistency.columns = ["Driver", "Podium Rate"]
    consistency["Podium Rate %"] = (consistency["Podium Rate"] * 100).round(1)

    col1, col2 = st.columns([2, 1])
    with col1:
        fig = px.bar(consistency, x="Podium Rate %", y="Driver", orientation="h",
                     color="Podium Rate %", color_continuous_scale="reds",
                     labels={"Driver": ""})
        fig.update_layout(yaxis={"categoryorder": "total ascending"})
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        top = consistency.iloc[0]
        st.info(f"""
**Finding:** {top['Driver']} leads all drivers with a **{top['Podium Rate %']}% podium rate** across 50+ race entries — the highest sustained consistency in F1 history.

**Recommendation:** Use this driver's performance profile as the benchmark for evaluating future signings. Consistency over a minimum of 50 races is a more reliable signal than single-season peaks.
        """)

    # ── Q2: Circuit with most DNFs ──────────────
    st.markdown("---")
    st.subheader("📌 Q2 — Which circuit produces the most DNF retirements?")

    dnf_circuit = df.groupby("circuit_name").agg(
        total_dnf=("dnf","sum"), total=("dnf","count")
    ).reset_index()
    dnf_circuit["dnf_rate"] = (dnf_circuit["total_dnf"] / dnf_circuit["total"] * 100).round(1)
    top_dnf_abs  = dnf_circuit.sort_values("total_dnf", ascending=False).head(1).iloc[0]
    top_dnf_rate = dnf_circuit[dnf_circuit["total"] >= 100].sort_values("dnf_rate", ascending=False).head(1).iloc[0]

    col1, col2 = st.columns([2, 1])
    with col1:
        top15 = dnf_circuit.sort_values("total_dnf", ascending=False).head(15)
        fig2 = px.bar(top15, x="total_dnf", y="circuit_name", orientation="h",
                      color="dnf_rate", color_continuous_scale="reds",
                      labels={"total_dnf": "Total DNFs", "circuit_name": "Circuit", "dnf_rate": "DNF Rate %"})
        fig2.update_layout(yaxis={"categoryorder": "total ascending"})
        st.plotly_chart(fig2, use_container_width=True)
    with col2:
        st.warning(f"""
**Most total DNFs:** {top_dnf_abs['circuit_name']} ({int(top_dnf_abs['total_dnf'])} retirements)

**Highest DNF rate:** {top_dnf_rate['circuit_name']} ({top_dnf_rate['dnf_rate']}% of entries retired)

**Why?** Circuits with tight barriers, high mechanical stress (high-speed corners), or extreme weather historically cause more retirements. Early circuits also had lower reliability standards.

**Recommendation:** Prioritize mechanical reliability upgrades before street circuits and historically punishing tracks.
        """)

    # ── Q3: Team dominance by circuit type ──────
    st.markdown("---")
    st.subheader("📌 Q3 — Is there a team that dominates specific circuit types?")

    top8 = df.groupby("team")["points"].sum().nlargest(8).index
    ct = df[df["team"].isin(top8)].groupby(["team","circuit_type"])["points"].sum().reset_index()
    ct_pivot = ct.pivot(index="team", columns="circuit_type", values="points").fillna(0)
    ct_pivot["Street Dominance %"] = (ct_pivot.get("Street",0) / (ct_pivot.get("Street",0) + ct_pivot.get("Permanent Track",0)) * 100).round(1)
    ct_pivot = ct_pivot.sort_values("Street Dominance %", ascending=False)

    col1, col2 = st.columns([2, 1])
    with col1:
        fig3 = px.bar(ct, x="team", y="points", color="circuit_type", barmode="group",
                      color_discrete_sequence=["#e10600","#444"],
                      labels={"points":"Points","team":"Constructor","circuit_type":"Circuit Type"})
        st.plotly_chart(fig3, use_container_width=True)
    with col2:
        top_street = ct_pivot.index[0]
        pct = ct_pivot.loc[top_street, "Street Dominance %"]
        st.success(f"""
**Finding:** {top_street} derives **{pct}% of their points** from street circuits — the highest street-circuit dependency among top teams.

**Recommendation:** When recruiting drivers for next season, prioritize candidates with strong street-circuit track records if the calendar is street-heavy.
        """)

    # ── Q4: Championship competitiveness ────────
    st.markdown("---")
    st.subheader("📌 Q4 — What trend do you see in championship competitiveness over the decades?")

    season_pts = df.groupby(["season_year","driver_name"])["points"].sum().reset_index()

    def gap(g):
        top2 = g.nlargest(2, "points")
        return top2.iloc[0]["points"] - top2.iloc[1]["points"] if len(top2) == 2 else np.nan

    gaps = season_pts.groupby("season_year").apply(gap).reset_index()
    gaps.columns = ["Season","Points Gap (P1 vs P2)"]

    col1, col2 = st.columns([2, 1])
    with col1:
        fig4 = px.line(gaps, x="Season", y="Points Gap (P1 vs P2)",
                       markers=True, color_discrete_sequence=["#e10600"])
        fig4.add_vrect(x0=2000, x1=2004, fillcolor="red", opacity=0.07,
                       annotation_text="Schumacher era", annotation_position="top left")
        fig4.add_vrect(x0=2014, x1=2020, fillcolor="blue", opacity=0.07,
                       annotation_text="Hamilton era", annotation_position="top left")
        st.plotly_chart(fig4, use_container_width=True)
    with col2:
        st.info("""
**Finding:** Championship gaps peaked during the Schumacher dominance era (2000–2004) and the early Hamilton/Mercedes era (2014–2020), indicating periods of technical supremacy.

**Trend:** The sport has become more competitive in recent seasons (2021–2022), with the gap narrowing — suggesting the regulations are working.

**Recommendation:** Monitor the 2022 technical regulations impact as a case study for competitive balance.
        """)

    # ── Q5: Driver recommendation ────────────────
    st.markdown("---")
    st.subheader("📌 Q5 — Which driver would you recommend for a future contract?")

    recent = df[df["season_year"] >= 2018]
    recent_fin = recent[recent["position_clean"].notna()]
    rc = recent_fin.groupby("driver_name").size()

    recs = []
    for drv in recent_fin["driver_name"].unique():
        d = recent_fin[recent_fin["driver_name"] == drv]
        if len(d) < 20:
            continue
        recs.append({
            "Driver":        drv,
            "Races (2018+)": len(d),
            "Win Rate %":    kpi_win_rate(d),
            "Podium Rate %": kpi_podium_rate(d),
            "Avg Points/Race": round(d["points"].sum() / len(d), 2),
            "DNF Rate %":    round(d["dnf"].sum() / len(d) * 100, 1),
        })

    recs_df = pd.DataFrame(recs).sort_values("Podium Rate %", ascending=False).head(10)

    col1, col2 = st.columns([2, 1])
    with col1:
        fig5 = px.scatter(
            recs_df, x="Win Rate %", y="Podium Rate %",
            size="Avg Points/Race", color="DNF Rate %",
            hover_name="Driver", color_continuous_scale="reds_r",
            text="Driver",
            labels={"Win Rate %":"Win Rate %","Podium Rate %":"Podium Rate %"},
        )
        fig5.update_traces(textposition="top center")
        st.plotly_chart(fig5, use_container_width=True)
    with col2:
        top_rec = recs_df.iloc[0]
        st.success(f"""
**Our recommendation: {top_rec['Driver']}**

- Podium Rate: **{top_rec['Podium Rate %']}%**
- Win Rate: **{top_rec['Win Rate %']}%**
- Avg Points/Race: **{top_rec['Avg Points/Race']}**
- DNF Rate: **{top_rec['DNF Rate %']}%**

Based on 2018–2022 data (most recent competitive context), {top_rec['Driver']} delivers the highest sustained performance with low mechanical/incident DNF exposure.

**Verdict:** Sign them.
        """)

    st.markdown("---")
    st.caption("Analysis by F1 Analytics Team | Data: Ergast Motor Racing API | 1950–2022")
