
import folium
from folium import plugins
import os
import webbrowser

# Approximate study locations
locations = {
    "Alankar Chowk": [18.52814, 73.875929],
    "Jehangir Hospital Chowk": [18.53038, 73.87666],
    "RTO Chowk - Sangam Bridge": [18.529529, 73.862219]
}

# Create map
m = folium.Map(
    location=[18.5295, 73.8695],
    zoom_start=15,
    tiles=None,
    control_scale=True,
    max_zoom=19
)

# OpenStreetMap France tile server
folium.TileLayer(
    tiles="https://{s}.tile.openstreetmap.fr/osmfr/{z}/{x}/{y}.png",
    attr='&copy; OpenStreetMap contributors',
    name="OpenStreetMap",
    subdomains=["a", "b", "c"],
    max_zoom=20,
    max_native_zoom=19
).add_to(m)

# Add markers and permanently visible labels
for name, coords in locations.items():

    folium.Marker(
        location=coords,
        tooltip=name,
        popup=f"<b>{name}</b>",
        icon=folium.Icon(
            color="red",
            icon="info-sign"
        )
    ).add_to(m)

    # Permanent location label
    folium.Marker(
        location=coords,
        icon=folium.DivIcon(
            html=f"""
            <div style="
                font-size: 13px;
                font-weight: bold;
                color: #111827;
                background: white;
                border: 1px solid #333;
                border-radius: 5px;
                padding: 5px 8px;
                width: 190px;
                box-shadow: 1px 1px 4px #777;
                white-space: normal;
            ">
                {name}
            </div>
            """,
            icon_size=(200, 40),
            icon_anchor=(-10, 15)
        )
    ).add_to(m)

# Approximate study-area boundary
latitudes = [p[0] for p in locations.values()]
longitudes = [p[1] for p in locations.values()]

bounds = [
    [min(latitudes) - 0.001, min(longitudes) - 0.001],
    [max(latitudes) + 0.001, max(longitudes) + 0.001]
]

folium.Rectangle(
    bounds=bounds,
    color="blue",
    weight=3,
    fill=True,
    fill_color="blue",
    fill_opacity=0.07,
    tooltip="Approximate study-area extent"
).add_to(m)

m.fit_bounds(bounds)

folium.LayerControl().add_to(m)
plugins.MeasureControl().add_to(m)

# Save to a new HTML file
output = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "Pune_Study_Area_FINAL.html"
)

m.save(output)

webbrowser.open("file:///" + output.replace("\\", "/"))

print("Map saved successfully:", output)
