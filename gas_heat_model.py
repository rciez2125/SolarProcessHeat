"""
A minimal Pyomo model: meet an hourly heat demand with a natural gas burner.

Decisions:
    gas_mw   - burner size (MW of heat), chosen once
    gas[t]   - heat from the burner in each hour t (MW)

Units: MW, MWh, $. One time step = 1 hour.
"""
from pyomo.environ import (
    ConcreteModel, Set, Param, Var, Constraint, Objective,
    NonNegativeReals, minimize,
)


def build_model(demand_mw, p):
    """
    demand_mw : list of hourly heat demand (MW)
    p         : dict of cost and performance assumptions
    """
    m = ConcreteModel()

    # Set: the hours being modeled
    m.T = Set(initialize=range(len(demand_mw)))

    # Parameter: hourly demand (input data)
    m.demand = Param(m.T, initialize=dict(enumerate(demand_mw)))

    # Variables
    m.gas_mw = Var(within=NonNegativeReals)        # burner size
    m.gas = Var(m.T, within=NonNegativeReals)      # hourly heat from gas

    # Constraint: the burner can't produce more than its size
    def capacity_rule(m, t):
        return m.gas[t] <= m.gas_mw
    m.capacity = Constraint(m.T, rule=capacity_rule)

    # Constraint: meet demand every hour
    def demand_rule(m, t):
        return m.gas[t] == m.demand[t]
    m.meet_demand = Constraint(m.T, rule=demand_rule)

    # Objective: annual cost = annualized capital cost + fuel cost
    capital = p["gas_capex"] * p["crf"] * m.gas_mw
    fuel = p["fuel_cost"] / p["gas_eff"] * sum(m.gas[t] for t in m.T)
    m.total_cost = Objective(expr=capital + fuel, sense=minimize)

    return m
