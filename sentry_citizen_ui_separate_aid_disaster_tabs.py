import pandas as pd
import plotly.express as px
import streamlit as st
import requests
import xml.etree.ElementTree as ET

st.set_page_config(page_title="SENTRY | Global Overview", page_icon="🌍", layout="wide")

# ---------- Data helpers ----------
@st.cache_data(ttl=3600, show_spinner=False)
def fetch_iati_aid():
    response = requests.get(
        "https://datastore.iati.cloud/api/v2/activity/",
        params={"q": "humanitarian:true", "rows": 100, "wt": "json"},
        timeout=20,
    )
    response.raise_for_status()
    records = response.json().get("response", {}).get("docs", [])
    return pd.DataFrame(records)


@st.cache_data(ttl=900, show_spinner=False)
def fetch_disaster_alerts():
    response = requests.get(
        "https://www.gdacs.org/xml/rss.xml",
        timeout=20,
        headers={"User-Agent": "SENTRY-dashboard/1.0"},
    )
    response.raise_for_status()
    root = ET.fromstring(response.content)
    ns = {"geo": "http://www.w3.org/2003/01/geo/wgs84_pos#"}
    rows = []
    for item in root.findall(".//item"):
        def field(name):
            node = item.find(name)
            return (node.text or "").strip() if node is not None else ""
        lat = lon = None
        point = item.find("geo:point", ns)
        if point is not None and point.text:
            parts = point.text.strip().split()
            if len(parts) >= 2:
                try:
                    lat, lon = float(parts[0]), float(parts[1])
                except ValueError:
                    pass
        rows.append({
            "Event": field("title"), "Description": field("description"),
            "Published": field("pubDate"), "Link": field("link"),
            "Latitude": lat, "Longitude": lon,
        })
    return pd.DataFrame(rows)


def first_value(value):
    if isinstance(value, list):
        return value[0] if value else ""
    return value if value is not None else ""


ISO2_TO_ISO3 = {
    "AF":"AFG", "BF":"BFA", "BR":"BRA", "ET":"ETH", "GA":"GAB",
    "HT":"HTI", "IN":"IND", "JP":"JPN", "ML":"MLI", "MM":"MMR",
    "NE":"NER", "SD":"SDN", "SY":"SYR", "UA":"UKR", "YE":"YEM",
}

# Friendly names where available; the ISO code remains visible for clarity.
def country_name(code):
    try:
        import pycountry
        country = pycountry.countries.get(alpha_3=str(code).upper())
        if country:
            return country.name
    except (ImportError, LookupError):
        pass
    fallback = {"USA":"United States", "GBR":"United Kingdom", "RUS":"Russia", "KOR":"South Korea", "PRK":"North Korea", "TUR":"Türkiye", "IRN":"Iran", "SYR":"Syria", "VEN":"Venezuela", "TZA":"Tanzania", "BOL":"Bolivia", "MDA":"Moldova", "LAO":"Laos", "VNM":"Vietnam", "COD":"Democratic Republic of the Congo"}
    return fallback.get(str(code).upper(), str(code).upper())

# ---------- Calm, citizen-friendly visual system ----------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Manrope:wght@500;600;700;800&display=swap');
:root { --bg:#0d1420; --panel:#141f2e; --line:#283548; --text:#eef3f8; --muted:#a5b2c2; --teal:#72d7c4; }
.stApp { background:var(--bg); color:var(--text); font-family:'DM Sans',sans-serif; }
.block-container { max-width:1360px; padding-top:1.5rem; padding-bottom:3rem; }
[data-testid="stSidebar"] { background:#101a28; border-right:1px solid var(--line); }
[data-testid="stSidebar"] * { color:var(--text); }
h1,h2,h3 { font-family:'Manrope',sans-serif !important; letter-spacing:-.025em; }
h1 { font-size:2.25rem !important; font-weight:800 !important; }
h2 { font-size:1.35rem !important; }
p, label, .stCaption { color:var(--muted); }
[data-testid="stMetric"] { background:var(--panel); border:1px solid var(--line); padding:15px 17px; border-radius:14px; }
[data-testid="stMetricLabel"] { color:var(--muted) !important; font-size:.84rem !important; }
[data-testid="stMetricValue"] { color:var(--text) !important; font-family:'Manrope',sans-serif; }
[data-testid="stPlotlyChart"] { border:1px solid var(--line); border-radius:14px; overflow:hidden; background:#101a28; }
[data-testid="stDataFrame"] { border:1px solid var(--line); border-radius:12px; overflow:hidden; }
.stButton>button, .stDownloadButton>button { border-radius:10px; }

/* Keep Streamlit's native controls inside the same dark visual theme. */
[data-testid="stFileUploaderDropzone"] {
    background: #141f2e !important;
    border: 1px dashed #40516a !important;
    border-radius: 12px !important;
}
[data-testid="stFileUploaderDropzone"] * {
    color: #eef3f8 !important;
}
[data-testid="stFileUploaderDropzone"] button {
    background: #203246 !important;
    border: 1px solid #40516a !important;
    color: #eef3f8 !important;
}
[data-testid="stFileUploaderDropzone"] button:hover {
    background: #29435a !important;
    border-color: #72d7c4 !important;
}
[data-testid="stFileUploaderDropzone"] small,
[data-testid="stFileUploaderDropzone"] span {
    color: #a5b2c2 !important;
}
[data-testid="stRadio"] label,
[data-testid="stCheckbox"] label {
    color: #eef3f8 !important;
}
[data-testid="stRadio"] [role="radiogroup"] {
    gap: .35rem;
}
[data-testid="stCheckbox"] [data-testid="stCheckbox"] {
    background: transparent !important;
}
[data-baseweb="select"] > div {
    background: #141f2e !important;
    border-color: #40516a !important;
    color: #eef3f8 !important;
}
[data-baseweb="popover"] [role="listbox"],
[data-baseweb="menu"] {
    background: #141f2e !important;
    border: 1px solid #40516a !important;
}
[data-baseweb="popover"] [role="option"] {
    color: #eef3f8 !important;
}
hr { border-color:var(--line); }
.sentry-head { display:flex; gap:13px; align-items:center; margin-bottom:4px; }
.sentry-logo { display:flex; align-items:center; justify-content:center; width:43px; height:43px; border-radius:13px; background:var(--teal); color:#10232b; font-family:'Manrope',sans-serif; font-weight:800; font-size:23px; }
.kicker { color:var(--teal); font-size:.72rem; font-weight:700; letter-spacing:.13em; text-transform:uppercase; margin-bottom:3px; }
.subline { color:var(--muted); font-size:.98rem; margin:0 0 1rem; }
.note { background:#152638; border:1px solid #2a4658; border-left:3px solid var(--teal); border-radius:10px; padding:12px 15px; color:#d7e3ee; font-size:.9rem; }
div[data-testid="stAlert"] { border-radius:12px; }

/* Lock the app into its dark presentation and hide Streamlit's menu,
   which otherwise exposes System/Light/Dark theme switching. */
[data-testid="stMainMenu"] { display: none !important; }
#MainMenu { visibility: hidden !important; }

</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="sentry-head"><div class="sentry-logo">S</div><div>
<div class="kicker">A clearer view of global events</div>
<h1 style="margin:0;line-height:1.1">SENTRY</h1>
</div></div>
<p class="subline">Explore country-level risk indicators, humanitarian activity and disaster alerts.</p>
<div class="note">Use this dashboard as a starting point for understanding reported signals—not as a prediction or a substitute for official guidance.</div>
""", unsafe_allow_html=True)

with st.sidebar:
    st.markdown("### Your view")


    uploaded = "sentry_dashboard_data (1).csv"
    # uploaded = st.file_uploader("Choose risk data (CSV)", type=["csv"], help="The CSV should include iso3, week, risk_score, warning_level and hostility_score.")
    metric_label_choice = st.radio("Colour the map by", ["Instability risk", "Hostility signal"], index=0)
    st.divider()
    st.markdown("### Optional information")
    show_aid = st.checkbox("Humanitarian aid activity", value=False)
    show_disasters = st.checkbox("Current disaster alerts", value=False)
    st.caption("Optional layers load from external data sources when selected.")

if uploaded is None:
    st.markdown("## Start with the global overview")
    st.write("Upload the risk-data CSV to explore the map and country details.")
    with st.expander("What should the CSV contain?"):
        st.code("iso3,week,risk_score,warning_level,hostility_score", language="text")
        st.write("Use ISO-3 country codes (for example, IND), dates in the `week` column, and numeric scores. Risk scores are expected on a 0–100 scale.")
    st.stop()

try:
    df = pd.read_csv(uploaded)
except Exception as exc:
    st.error(f"We couldn't read that CSV file. Check that it is a valid CSV and try again. Details: {exc}")
    st.stop()

required = {"iso3", "week", "risk_score", "warning_level", "hostility_score"}
missing = required - set(df.columns)
if missing:
    st.error("This file is missing required columns: " + ", ".join(sorted(missing)))
    st.stop()

df["iso3"] = df["iso3"].astype(str).str.upper().str.strip()
df["week"] = pd.to_datetime(df["week"], errors="coerce")
df["risk_score"] = pd.to_numeric(df["risk_score"], errors="coerce")
df["hostility_score"] = pd.to_numeric(df["hostility_score"], errors="coerce")
df = df.dropna(subset=["iso3"])
if df.empty:
    st.error("No usable country records were found in this file.")
    st.stop()

# Show one latest record per country so the map and headline counts are not inflated by history.
df = df.sort_values("week").drop_duplicates(subset=["iso3"], keep="last")
latest_date = df["week"].max()
metric_col = "risk_score" if metric_label_choice == "Instability risk" else "hostility_score"
metric_title = "Instability risk score" if metric_col == "risk_score" else "Hostility signal"

if pd.notna(latest_date):
    st.caption(f"Latest date in uploaded data: {latest_date:%d %b %Y}")
else:
    st.caption("The uploaded data does not contain a readable date.")

m1, m2, m3 = st.columns(3, gap="medium")
m1.metric("Countries included", f"{df['iso3'].nunique():,}")
warning_count = int((df["warning_level"].astype(str).str.upper() == "WARNING").sum())
m2.metric("Marked for attention", f"{warning_count:,}", help="Count of countries whose latest uploaded record is labelled WARNING.")
max_risk = df["risk_score"].max()
m3.metric("Highest risk score", f"{max_risk:.1f} / 100" if pd.notna(max_risk) else "—", help="The maximum score in the latest available record for each country. It is not a probability.")

if pd.notna(latest_date) and latest_date < pd.Timestamp.now().normalize() - pd.Timedelta(days=120):
    st.warning("The risk dataset appears older than four months. The map shows the uploaded data date; it is not a live risk forecast.")

# ---------- Main tabs keep the default screen simple ----------
overview_tab, country_tab, aid_tab, disaster_tab = st.tabs(["🌍  Global overview", "🔎  Explore a country", "🤝  Humanitarian aid", "🚨  Disaster alerts"])

with overview_tab:
    st.subheader("Global overview")
    st.caption(f"Map colour shows {metric_title.lower()}. Hover over a country to see its values.")
    map_df = df.dropna(subset=[metric_col]).copy()
    if map_df.empty:
        st.info("There are no numeric values available for this map layer.")
    else:
        hover = {"iso3": False, "risk_score": ":.1f", "warning_level": True, "hostility_score": ":.2f"}
        if metric_col == "risk_score":
            scale, limits = "YlOrRd", (0, 100)
        else:
            scale, limits = "RdBu_r", None
        fig = px.choropleth(
            map_df, locations="iso3", locationmode="ISO-3", color=metric_col,
            hover_name=map_df["iso3"].map(country_name), hover_data=hover,
            color_continuous_scale=scale, range_color=limits,
            labels={"risk_score":"Risk score (0–100)", "hostility_score":"Hostility signal", "warning_level":"Status"},
        )
        fig.update_layout(
            height=500, margin=dict(l=0, r=0, t=4, b=0),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font=dict(family="DM Sans, sans-serif", color="#e6edf5"),
            geo=dict(showframe=False, showcoastlines=True, coastlinecolor="#53677c", showland=True,
                     landcolor="#1b2a3b", showocean=True, oceancolor="#101a28", showcountries=True,
                     countrycolor="#35465a", bgcolor="rgba(0,0,0,0)", projection_type="natural earth"),
            coloraxis_colorbar=dict(title=dict(text=metric_title, font=dict(color="#e6edf5")), tickfont=dict(color="#b8c4d2")),
        )
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False, "scrollZoom": False})

    with st.expander("View country ranking"):
        ranking = df.sort_values(metric_col, ascending=(metric_col != "risk_score"), na_position="last").copy()
        ranking["Country"] = ranking["iso3"].map(country_name)
        ranking_view = ranking[["Country", "iso3", "risk_score", "warning_level", "hostility_score"]].rename(columns={
            "iso3":"Code", "risk_score":"Risk score", "warning_level":"Status", "hostility_score":"Hostility signal"
        })
        st.dataframe(ranking_view, use_container_width=True, hide_index=True, height=320,
                     column_config={"Risk score":st.column_config.NumberColumn(format="%.1f"), "Hostility signal":st.column_config.NumberColumn(format="%.2f")})

with country_tab:
    st.subheader("Explore a country")
    st.caption("Choose a country to see the latest values available in your uploaded dataset.")
    countries = sorted(df["iso3"].unique(), key=country_name)
    labels = {code: f"{country_name(code)} ({code})" for code in countries}
    selected = st.selectbox("Country", countries, format_func=lambda code: labels[code], label_visibility="collapsed")
    country = df[df["iso3"] == selected].iloc[-1]
    a, b = st.columns([1, 2], gap="large")
    with a:
        st.markdown(f"### {country_name(selected)}")
        st.caption(f"Country code: {selected}")
        st.metric("Instability risk", f"{country['risk_score']:.1f} / 100" if pd.notna(country["risk_score"]) else "Not available")
        st.metric("Hostility signal", f"{country['hostility_score']:.2f}" if pd.notna(country["hostility_score"]) else "Not available")
        status = str(country.get("warning_level", "Not provided"))
        st.write(f"**Dataset status:** {status}")
    with b:
        st.markdown("### How to read these figures")
        st.write("Risk score is a model-derived indicator on a 0–100 scale. The hostility signal is a separate dataset measure and may not be comparable across countries.")
        st.write("Neither score should be treated as a confirmed event, a personal safety assessment, or a calibrated probability.")
        st.caption("Country values reflect the latest record for each country in the uploaded file.")

with aid_tab:
    st.subheader("Humanitarian aid activity")
    st.caption("Reported activities by recipient country from the IATI datastore. Activity counts do not indicate funding amounts or confirm delivery.")
    if not show_aid:
        st.info("Turn on **Humanitarian aid activity** in the sidebar to load this layer.")
    else:
        st.markdown("### Humanitarian aid")
        st.caption("Reported activities by recipient country (IATI)")
        if not show_aid:
            st.info("Turn on **Humanitarian aid activity** in the sidebar to load this map.")
        else:
            try:
                aid_df = fetch_iati_aid()
                if aid_df.empty:
                    st.info("No matching aid activities were returned by IATI.")
                elif "recipient_country_code" not in aid_df.columns:
                    st.warning("The feed returned records, but recipient-country information was not available in the expected field.")
                else:
                    aid_df["country_iso3"] = aid_df["recipient_country_code"].apply(first_value).astype(str).str.upper().map(ISO2_TO_ISO3)
                    aid_df = aid_df.dropna(subset=["country_iso3"]).copy()
                    aid_df["Country"] = aid_df["country_iso3"].map(country_name)

                    if aid_df.empty:
                        st.info("No returned activities had a recognised recipient-country code.")
                    else:
                        aid_counts = aid_df.groupby(["country_iso3", "Country"]).size().reset_index(name="Reported activities")
                        aid_map = px.choropleth(
                            aid_counts,
                            locations="country_iso3",
                            locationmode="ISO-3",
                            color="Reported activities",
                            hover_name="Country",
                            hover_data={"country_iso3": False, "Reported activities": True},
                            color_continuous_scale=["#173047", "#3d8eaa", "#72d7c4"],
                        )
                        aid_map.update_layout(
                            height=360,
                            margin=dict(l=0, r=0, t=8, b=8),
                            paper_bgcolor="rgba(0,0,0,0)",
                            plot_bgcolor="rgba(0,0,0,0)",
                            geo=dict(
                                showframe=False, showcoastlines=True, coastlinecolor="#53677c",
                                showland=True, landcolor="#1b2a3b", showocean=True,
                                oceancolor="#101a28", bgcolor="rgba(0,0,0,0)",
                                projection_type="natural earth",
                            ),
                            font=dict(color="#e6edf5"),
                            coloraxis_colorbar=dict(
                                title=dict(text="Activities", font=dict(color="#e6edf5")),
                                tickfont=dict(color="#aebed0"),
                            ),
                        )
                        st.plotly_chart(aid_map, use_container_width=True, config={"displayModeBar": False})
                        st.markdown("### Reported activity locations")
                        ############################################################################
                        
                        location_rows = []
                        
                        for _, row in aid_df.iterrows():
                            positions = row.get("location_point_pos", [])
                            names = row.get("location_name_narrative", [])
                            
                            if not isinstance(positions, list):
                                continue
                            
                            if not isinstance(names, list):
                                names = []
                        
                            for i, position in enumerate(positions):
                                try:
                                    lat, lon = map(float, position.split())
                                except (ValueError, AttributeError):
                                    continue
                        
                                if not (-90 <= lat <= 90 and -180 <= lon <= 180):
                                    continue
                        
                                location_name = names[i] if i < len(names) else "Location not named"
                        
                                location_rows.append({
                                    "Location": str(location_name),
                                    "Latitude": lat,
                                    "Longitude": lon,
                                    "Activity": str(first_value(row.get("title_narrative_text")) or "Not provided"),
                                })
                        
                        if location_rows:
                            location_df = pd.DataFrame(location_rows)
                        ################################################################################
                            location_df["Get directions"] = location_df.apply(
                            lambda row: f"https://www.google.com/maps/dir/?api=1&destination={row['Latitude']},{row['Longitude']}",
                            axis=1,
                            )



                            location_map = px.scatter_geo(
                                location_df,
                                lat="Latitude",
                                lon="Longitude",
                                hover_name="Location",
                                hover_data=["Activity", "Latitude", "Longitude"],
                                projection="natural earth",
                            )
                        
                            location_map.update_traces(
                                marker=dict(size=8, color="#72d7c4", opacity=0.85)
                            )
                        
                            location_map.update_layout(
                                height=450,
                                margin=dict(l=0, r=0, t=10, b=10),
                                geo=dict(
                                    showland=True,
                                    landcolor="#1b2a3b",
                                    showocean=True,
                                    oceancolor="#101a28",
                                    showcountries=True,
                                    bgcolor="rgba(0,0,0,0)",
                                ),
                                font=dict(color="#e6edf5"),
                            )
                            st.dataframe(
                            location_df[["Location", "Activity", "Get directions"]],
                            use_container_width=True,
                            hide_index=True,
                            column_config={
                                "Get directions": st.column_config.LinkColumn(
                                    "Get directions",
                                    display_text="Open Google Maps",
                                )
                            },
                            )                        
                        
                            st.plotly_chart(
                                location_map,
                                use_container_width=True,
                                config={"displayModeBar": False},
                            )
                            st.caption(
                            f"Mapped {len(location_df)} reported location records. "
                            "These locations are reported by IATI and may not be exact aid-delivery sites. "
                            "Check the activity details before travelling."
                        )
                        else:
                            st.info("No valid activity coordinates were found.")

                        
                        
                        
                        
                        


                        



















































                    
                        st.caption(f"{len(aid_df)} reported activities across {aid_df['country_iso3'].nunique()} recognised recipient countries.")
                        def field_text(row, field):
                            value = first_value(row.get(field, ""))
                            return str(value) if value else "Not provided"
                        display = pd.DataFrame({
                            "Country": aid_df["Country"],
                            "Activity": aid_df.apply(lambda row: field_text(row, "title_narrative_text"), axis=1),
                            "Reporting organisation": aid_df.apply(lambda row: field_text(row, "reporting_org_narrative_text"), axis=1),
                            "IATI identifier": aid_df.apply(lambda row: field_text(row, "iati_identifier"), axis=1),
                        })
                        st.caption("Activity counts are not funding amounts and do not confirm aid delivery.")
                        st.dataframe(display, use_container_width=True, hide_index=True, height=260)
            except (requests.RequestException, ValueError, KeyError) as exc:
                st.error(f"Aid activity could not be loaded right now. Please try again later. Details: {exc}")

with disaster_tab:
    st.subheader("Current disaster alerts")
    st.caption("Reported events from the Global Disaster Alert and Coordination System (GDACS). Follow source links for official details.")
    if not show_disasters:
        st.info("Turn on **Current disaster alerts** in the sidebar to load this layer.")
    else:
        st.markdown("### Disaster alerts")
        st.caption("Current reported events (GDACS)")
        if not show_disasters:
            st.info("Turn on **Current disaster alerts** in the sidebar to load this map.")
        else:
            try:
                alerts = fetch_disaster_alerts()
                if alerts.empty:
                    st.info("No alerts were returned by GDACS.")
                else:
                    mapped = alerts.dropna(subset=["Latitude", "Longitude"]).copy()
                    if not mapped.empty:
                        alert_fig = px.scatter_geo(
                            mapped, lat="Latitude", lon="Longitude", hover_name="Event",
                            hover_data={"Published": True, "Latitude": False, "Longitude": False},
                            projection="natural earth",
                        )
                        alert_fig.update_traces(marker=dict(size=9, color="#ed826d", opacity=.88))
                        alert_fig.update_layout(
                            height=360, margin=dict(l=0, r=0, t=8, b=8),
                            paper_bgcolor="rgba(0,0,0,0)",
                            geo=dict(
                                showframe=False, showcoastlines=True, coastlinecolor="#53677c",
                                showland=True, landcolor="#1b2a3b", showocean=True,
                                oceancolor="#101a28", bgcolor="rgba(0,0,0,0)",
                                projection_type="natural earth",
                            ),
                            font=dict(color="#e6edf5"),
                        )
                        st.plotly_chart(alert_fig, use_container_width=True, config={"displayModeBar": False})
                        
                    else:
                        st.info("Alerts were returned, but the feed did not provide usable map coordinates.")
                    st.caption(f"{len(alerts)} alert records returned. Open the source for official details.")
                    st.dataframe(
                        alerts[["Event", "Published", "Link"]],
                        use_container_width=True, hide_index=True, height=260,
                        column_config={"Link": st.column_config.LinkColumn("Official source", display_text="Open alert")},
                    )
            except (requests.RequestException, ET.ParseError, ValueError) as exc:
                st.error(f"Disaster alerts could not be loaded right now. Please try again later. Details: {exc}")
st.divider()
st.caption("Data note: SENTRY is a prototype. Risk indicators depend on the uploaded dataset and may be historical. External aid and disaster feeds can be incomplete or temporarily unavailable. For urgent safety decisions, consult local authorities and official alerts.")
