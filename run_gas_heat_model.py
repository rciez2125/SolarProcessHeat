"""
Load the demand data, build the gas-only model, solve it, and print results.

Setup (once):  pip install pyomo highspy pandas
"""
import pandas as pd
from pyomo.environ import SolverFactory, value

from gas_heat_model import build_model

#Data
load = pd.read_csv("load_profiles/ethane_cracker_pilot_load_8760.csv")
demand_mw = load["total_MWth"].tolist()
# use Van Horn, TX as the location for the solar heat model

params = {
    "gas_capex": 200_000,   # $/MW of burner (placeholder), adjust as necessary
    "crf": 0.094,           # capital recovery factor (8%, 25 yr), adjust as necessary
    "fuel_cost": 13.65,     # $/MWh of fuel ($4/MMBtu), adjust as necessary
    "gas_eff": 0.90,        # heat delivered / fuel burned, adjust as necessary
}

# Build and solve
m = build_model(demand_mw, params)
SolverFactory("appsi_highs").solve(m) #if this is still too slow, try cplex 

# Results
print(f"Burner size:      {value(m.gas_mw):.2f} MW")
print(f"Annual heat:      {sum(demand_mw):,.0f} MWh")
print(f"Annual cost:      ${value(m.total_cost):,.0f}")
print(f"Cost of heat:     ${value(m.total_cost) / sum(demand_mw):.2f} /MWh")
