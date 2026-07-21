"""Builds Folium maps for the dashboard."""
import folium
from config import CORRIDORS, MOCK_VESSELS, ROUTE_COORDS, ROUTE_COLORS


def build_map(corridor_id: str, recommendations: list[dict]) -> folium.Map:
    """Create a Folium map showing corridor, vessels, and recommended routes."""
    c = CORRIDORS.get(corridor_id, CORRIDORS["hormuz"])
    m = folium.Map(
        location=[c["lat"], c["lon"]],
        zoom_start=c["zoom"],
        tiles="CartoDB dark_matter",
        attr="Rakshak AI",
    )

    # --- Corridor marker ---
    folium.CircleMarker(
        location=[c["lat"], c["lon"]],
        radius=18,
        color="#FF4444",
        fill=True,
        fill_opacity=0.25,
        popup=f"<b>{c['label']}</b><br>Monitored Corridor",
    ).add_to(m)

    # --- AIS vessel markers ---
    for v in MOCK_VESSELS:
        color = "#FF6B6B" if "Dark" in v["status"] else "#4ECDC4"
        icon = "ship" if v["type"] == "VLCC" else "anchor"
        folium.Marker(
            location=[v["lat"], v["lon"]],
            popup=f"<b>{v['name']}</b><br>{v['type']} — {v['status']}",
            icon=folium.Icon(color="red" if "Dark" in v["status"] else "blue",
                             icon=icon, prefix="fa"),
        ).add_to(m)

    # --- Recommended shipping routes ---
    for i, rec in enumerate(recommendations):
        route_key = rec.get("route", "")
        coords = ROUTE_COORDS.get(route_key)
        if not coords:
            # Try partial match
            for k, v in ROUTE_COORDS.items():
                if k.split("->")[0].strip() in route_key:
                    coords = v
                    break
        if coords:
            color = ROUTE_COLORS[i % len(ROUTE_COLORS)]
            folium.PolyLine(
                locations=coords,
                weight=3,
                color=color,
                opacity=0.8,
                dash_array="10 5",
                popup=f"<b>Route #{rec['rank']}</b><br>{rec['source_supplier']}<br>{route_key}",
            ).add_to(m)
            # Origin marker
            folium.CircleMarker(
                location=coords[0],
                radius=6,
                color=color,
                fill=True,
                fill_opacity=0.9,
                popup=f"Origin: {rec['source_supplier']}",
            ).add_to(m)
            # Destination marker
            folium.CircleMarker(
                location=coords[-1],
                radius=6,
                color=color,
                fill=True,
                fill_opacity=0.9,
                popup=f"Destination (India)",
            ).add_to(m)

    return m
