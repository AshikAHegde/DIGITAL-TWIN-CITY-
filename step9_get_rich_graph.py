import osmnx as ox

CITY_NAME = "Pune, Maharashtra, India"
RICH_GRAPH_FILE = "pune_rich_graph.graphml" 

print(f"Starting to download HIGH-DETAIL graph for {CITY_NAME}...")
print("This will take a few minutes...")

try:
    # 1. Download
    G = ox.graph_from_place(CITY_NAME, network_type='drive')
    
    # 2. Add speed/time
    print("Adding speed limit data...")
    G = ox.add_edge_speeds(G)
    
    print("Adding travel time data...")
    G = ox.add_edge_travel_times(G)

    # 3. Clean up for simulation
    print("Setting default lanes=1 and CLEANING/CASTING data types...")
    for u, v, k, data in G.edges(keys=True, data=True):
        
        # --- THIS IS THE FIX ---
        # 1. Get lanes, default to 1
        lanes_str = data.get('lanes', 1)
        # Handle cases where 'lanes' might be a list (e.g., '2;3')
        if isinstance(lanes_str, list):
            lanes_str = lanes_str[0] # Just take the first one
        # Force it to be an integer
        data['lanes'] = int(float(lanes_str)) 
        
        # 2. Get speed, default to 30
        speed_str = data.get('speed_kph', 30)
        # Force it to be a float
        data['speed_kph'] = float(speed_str)
        
        # 3. Get travel time
        travel_time_str = data.get('travel_time', data['length'] / (data['speed_kph'] * 1000 / 3600))
        # Force it to be a float
        data['travel_time'] = float(travel_time_str)
        
        # 4. Create a 'base_travel_time' that we will NOT change
        data['base_travel_time'] = data['travel_time']
        # --- END OF FIX ---

    print("\n--- Download Success! ---")
    
    # Save the new, rich graph
    ox.save_graphml(G, filepath=RICH_GRAPH_FILE)
    
    print(f"\nSuccessfully saved the new, correct, rich map to: {RICH_GRAPH_FILE}")
    print("This graph now contains speed and travel time AS NUMBERS.")
    print("--- Task 9 (Part 1) Complete ---")

except Exception as e:
    print(f"\n--- AN ERROR OCCURRED ---")
    print(f"Error: {e}")