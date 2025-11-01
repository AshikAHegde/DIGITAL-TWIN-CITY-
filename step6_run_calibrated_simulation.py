import pandas as pd
import os
import networkx as nx
import osmnx as ox
import random

# --- We import from agentpy ---
import agentpy as ap

# --- CONFIGURATION ---
DATA_FOLDER = "data"
VEHICLE_FILE = "pune-vehicle_registrations_2014-2020.csv"
GRAPH_FILE = "digital_twin_graph_v1.graphml"

# --- CALIBRATION SETTINGS ---
CALIBRATION_COLUMN = '2017-18' 
PERCENT_OF_CARS_ON_ROAD = 0.001 # 0.1% for a manageable test
NUM_STEPS = 10 

# --- 1. AGENT AND MODEL DEFINITION (AgentPy + Manual Grid) ---

class VehicleAgent(ap.Agent):
    """A single vehicle agent in the city."""
    
    def setup(self):
        """Called once when agent is created."""
        self.pos = 0 # Will be assigned by the model
        pass

    def step(self):
        """Defines the agent's behavior in one time step."""
        
        # Get all neighbors of the current node
        neighbors = list(self.model.G.neighbors(self.pos))
        
        if neighbors:
            # --- THIS IS THE FIX ---
            # The agent must use the MODEL's random number generator
            new_pos = self.model.random.choice(neighbors)
            
            # Use our model's manual move_agent function
            self.model.move_agent(self, new_pos)


class CityModel(ap.Model):
    """The main model for the city simulation."""
    
    def setup(self):
        """Called once when model is created."""
        
        print("Loading graph for simulation...")
        try:
            # Load the digital twin graph
            self.G = ox.load_graphml(GRAPH_FILE)
            self.graph_nodes = list(self.G.nodes())
            print(f"Graph loaded with {len(self.graph_nodes)} nodes.")
        except FileNotFoundError:
            print(f"--- FATAL ERROR: Cannot find {GRAPH_FILE} ---")
            return

        # 1. Create our own 'grid'
        print("Initializing manual grid...")
        self.grid = {node_id: set() for node_id in self.G.nodes()}
        
        # 2. Create an agent position tracker
        self.agent_positions = {}
        
        # Get number of agents from parameters
        num_agents = self.p.num_agents
        print(f"Creating {num_agents} vehicle agents (this may take a moment)...")

        # 3. Create agents
        self.agents = ap.AgentList(self, num_agents, VehicleAgent)
        
        # 4. Place agents on the grid manually
        initial_positions = self.random.choices(self.graph_nodes, k=num_agents) 
        
        for i, agent in enumerate(self.agents):
            pos = initial_positions[i]
            agent.pos = pos                # Tell agent its position
            self.grid[pos].add(agent)      # Add agent to the grid
            self.agent_positions[agent.id] = pos # Add agent to tracker

        print("All agents created and placed on manual grid.")

    def move_agent(self, agent, new_pos):
        """Manually moves an agent from its current position to a new one."""
        current_pos = agent.pos
        self.grid[current_pos].remove(agent)
        self.grid[new_pos].add(agent)
        agent.pos = new_pos
        self.agent_positions[agent.id] = new_pos
        
    def step(self):
        """Called in each step of the simulation."""
        self.agents.step() # This calls the 'step' method of all agents

    def update(self):
        """Called after each step."""
        # For now, let's track Agent 0's position
        agent_0 = self.agents[0]
        pos_0 = agent_0.pos # We can now get it directly
        print(f"Position of Agent 0: {pos_0}")

    def end(self):
        """Called at the end of the simulation."""
        print("\n--- Simulation Complete ---")


# --- 2. CALIBRATION AND EXECUTION ---

def calibrate_agent_count():
    """Reads the vehicle data and returns a realistic agent count."""
    try:
        file_path = os.path.join(DATA_FOLDER, VEHICLE_FILE)
        df = pd.read_csv(file_path)
        
        total_vehicles = df[CALIBRATION_COLUMN].sum()
        realistic_num_agents = int(total_vehicles * PERCENT_OF_CARS_ON_ROAD)
        
        print(f"--- CALIBRATION SUCCESS ---")
        print(f"Total vehicles (from '{CALIBRATION_COLUMN}' column): {total_vehicles:,}")
        print(f"Agent count (at {PERCENT_OF_CARS_ON_ROAD*100}%): {realistic_num_agents:,}")
        return realistic_num_agents
        
    except FileNotFoundError:
        print(f"--- ERROR: File not found: {file_path} ---")
        return None
    except Exception as e:
        print(f"--- ERROR during calibration: {e} ---")
        return None

# --- Main function to run the simulation ---
if __name__ == "__main__":
    
    print("--- Starting Task 6: Calibrated City Simulation (AgentPy + Manual Grid) ---")
    
    NUM_AGENTS = calibrate_agent_count()
    
    if NUM_AGENTS:
        # 1. Setup model parameters
        parameters = {
            'num_agents': NUM_AGENTS,
            'steps': NUM_STEPS # AgentPy will run for 10 steps
        }
        
        # 2. Create the model
        model = CityModel(parameters)
        
        # 3. Run the simulation
        print("\n--- Running Simulation Steps ---")
        results = model.run()
        
    else:
        print("--- Simulation HALTED due to calibration error. ---")