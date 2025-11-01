import osmnx as ox
import networkx as nx
import pandas as pd
import os

DATA_FOLDER = "data"
MAP_FILE = "pune_road_network.graphml"

print("Starting Task 5 (v2): Building the Graph Layer...")
print(f"Loading base road network: {MAP_FILE}...")

# --- 1. Load the base road network ---
try:
    G = ox.load_graphml(MAP_FILE)
except FileNotFoundError:
    print(f"--- ERROR: Could not find {MAP_FILE} ---")
    print("Please run step1_get_map.py again to download it.")
    exit()

print(f"Base graph loaded: {len(G.nodes)} nodes, {len(G.edges)} edges.")

# --- 2. Create a list of dictionaries for data mapping ---
# This is smarter: we specify the exact column names for each file
data_to_map = [
    {
        "file": "healthcare_pune_clean.csv",
        "attr": "healthcare_amenity",
        "lat_col": "latitude",
        "lon_col": "longitude",
        "name_col": "name"
    },
    {
        "file": "bus_stops_clean.csv",
        "attr": "bus_stop",
        "lat_col": "stop_lat",  # <-- The fix is here
        "lon_col": "stop_lon",  # <-- The fix is here
        "name_col": "stop_name"
    },
    {
        "file": "metro_stations_clean.csv",
        "attr": "metro_station",
        "lat_col": "latitude",
        "lon_col": "longitude",
        "name_col": "station_name"
    },
    {
        "file": "aqi_pune_clean.csv",
        "attr": "aqi_station",
        "lat_col": "latitude",
        "lon_col": "longitude",
        "name_col": "station" # Using the 'station' col as the name
    }
]

for item in data_to_map:
    file_path = os.path.join(DATA_FOLDER, item['file'])
    try:
        print(f"\nProcessing {item['file']}...")
        df = pd.read_csv(file_path)

        # Use the specific lat/lon column names
        lat_col = item['lat_col']
        lon_col = item['lon_col']

        # Drop any rows with missing lat/lon
        df = df.dropna(subset=[lat_col, lon_col])

        # Get the list of coordinates
        lats = df[lat_col]
        lons = df[lon_col]

        # Find the nearest road node (intersection) for each point
        nearest_nodes = ox.nearest_nodes(G, X=lons, Y=lats)

        # Add this data as an attribute to the graph node
        for i, node_id in enumerate(nearest_nodes):
            # Get the name from the correct column
            name = df.iloc[i].get(item['name_col'], 1) # Use 1 if name is missing

            # Set the attribute on the node
            G.nodes[node_id][item['attr']] = name

        print(f"Successfully attached {len(df)} '{item['attr']}' points to the graph.")

    except FileNotFoundError:
        print(f"SKIPPING: File not found: {file_path}")
    except Exception as e:
        print(f"ERROR processing {item['file']}: {e}")

# --- 3. Save the new, enriched graph ---
output_file = "digital_twin_graph_v1.graphml"
ox.save_graphml(G, filepath=output_file)

print(f"\n--- SUCCESS! ---")
print(f"Saved new enriched graph to: {output_file}")
print("This graph now contains your road network AND your amenities data.")
print("\n--- Task 5 Complete ---")