"""
Fixed hourly heat-demand profile for a small (demonstration-scale) ethane
cracking furnace, split into a PREHEAT duty and a RADIANT duty.

Run:  python make_cracker_load.py   ->  writes ethane_cracker_pilot_load_8760.csv

Scale
-----
One furnace producing 2.5 t/h ethylene (~21 kt/yr at 95% availability), i.e.
~4.8 t/h ethane through the coils and ~7.5 MWth of process heat. That is about
the size of the electrically heated demonstration furnaces built in 2024
(~6 MW, ~4 t/h hydrocarbon feed). A world-scale cracker has ~8-12 furnaces
that are each 10-20x larger.

Duty definitions (heat absorbed by the process, NOT fuel fired)
---------------------------------------------------------------
PREHEAT : heats ethane feed (incl. recycle) and dilution steam from inlet
          conditions to the radiant-coil inlet ("crossover") temperature.
          In a gas-fired furnace this is done in the convection section by flue
          gas. Delivery temperature needed: ~650 C.
RADIANT : heats the mixture from crossover to coil-outlet temperature (COT) AND
          supplies the endothermic heat of cracking. Process gas reaches
          ~850 C, so the heat source must be well above that (fired-furnace
          firebox ~1100-1200 C; tube metal ~1000-1050 C).
Not included: the steam raised in the transfer-line exchangers (it comes from
cooling the cracked gas, so it does not need solar heat) and the compressors
and refrigeration in the separation train (electric/steam loads elsewhere in
the plant).

Operating schedule
------------------
Flat at design rate, except for decoking: one 36 h decoke every 50 days.
During decoking there is no feed, and the coil is held hot for the steam/air
burn-off. That is modeled as a fraction of design duty (DECOKE_* below).
The `mode` column lets students choose to ignore decoking (treat every hour as
"crack") if they want a perfectly flat load.

All property values are rounded averages over the temperature range, which is
fine for a class problem. Change the parameters below to rescale.
"""
import numpy as np
import pandas as pd

# ---- design parameters --------------------------------------------------
ETHYLENE_T_PER_H = 2.5      # design ethylene production rate
ETHYLENE_YIELD_PER_PASS = 0.52  # kg C2H4 per kg ethane through the coil (~65% conversion)
STEAM_TO_HC = 0.30          # kg dilution steam per kg ethane

T_ETHANE_IN = 60.0          # C, ethane feed + recycle entering the furnace
T_STEAM_IN = 180.0          # C, saturated dilution steam (~10 bar) from the plant steam system
T_CROSSOVER = 650.0         # C, radiant-coil inlet
T_COT = 850.0               # C, coil outlet temperature

CP_ETHANE_PREHEAT = 2.70    # kJ/kg-K, mean cp of ethane, 60 -> 650 C
CP_STEAM_PREHEAT = 2.10     # kJ/kg-K, mean cp of steam, 180 -> 650 C
CP_GAS_RADIANT = 3.60       # kJ/kg-K, mean cp of the hydrocarbon mix, 650 -> 850 C
CP_STEAM_RADIANT = 2.30     # kJ/kg-K, mean cp of steam, 650 -> 850 C

DH_RXN_KJ_PER_MOL = 144.0   # C2H6 -> C2H4 + H2 at ~1100 K
MW_ETHYLENE = 28.05         # g/mol
SIDE_RXN_ALLOWANCE = 1.05   # +5% for byproduct reactions (CH4, C3+, etc.)

DECOKE_EVERY_DAYS = 50
DECOKE_HOURS = 36
DECOKE_FIRST_START_H = 24 * 20     # first decoke starts on day 21
DECOKE_PREHEAT_FRAC = 0.15         # fraction of design preheat duty during decoke
DECOKE_RADIANT_FRAC = 0.25         # fraction of design radiant duty during decoke

YEAR = 2023  # dummy non-leap year, local standard time (matches the Daggett TMY notebook)

# ---- design-point energy balance (per tonne ethylene, GJ/t) -------------
ethane_t = 1.0 / ETHYLENE_YIELD_PER_PASS          # t ethane through coil per t C2H4
steam_t = STEAM_TO_HC * ethane_t                  # t dilution steam per t C2H4
MJ = 1e-3                                         # kJ/kg * t = MJ  ->  convert to GJ below

preheat_gj_t = (ethane_t * CP_ETHANE_PREHEAT * (T_CROSSOVER - T_ETHANE_IN)
                + steam_t * CP_STEAM_PREHEAT * (T_CROSSOVER - T_STEAM_IN)) * MJ
radiant_sensible_gj_t = (ethane_t * CP_GAS_RADIANT
                         + steam_t * CP_STEAM_RADIANT) * (T_COT - T_CROSSOVER) * MJ
reaction_gj_t = DH_RXN_KJ_PER_MOL * (1e6 / MW_ETHYLENE) * 1e-6 * SIDE_RXN_ALLOWANCE
radiant_gj_t = radiant_sensible_gj_t + reaction_gj_t

preheat_mw = preheat_gj_t * ETHYLENE_T_PER_H / 3.6     # GJ/h -> MW
radiant_mw = radiant_gj_t * ETHYLENE_T_PER_H / 3.6

# ---- hourly profile -----------------------------------------------------
idx = pd.date_range(f"{YEAR}-01-01 00:00", periods=8760, freq="h")
hour = np.arange(8760)
decoke = np.zeros(8760, dtype=bool)
for start in range(DECOKE_FIRST_START_H, 8760, DECOKE_EVERY_DAYS * 24):
    decoke[start:start + DECOKE_HOURS] = True

df = pd.DataFrame(index=idx)
df.index.name = "timestamp_local_standard"
df["hour_of_year"] = hour + 1
df["mode"] = np.where(decoke, "decoke", "crack")
df["ethylene_t_per_h"] = np.where(decoke, 0.0, ETHYLENE_T_PER_H)
df["ethane_feed_t_per_h"] = np.where(decoke, 0.0, ETHYLENE_T_PER_H * ethane_t)
df["preheat_MWth"] = np.where(decoke, DECOKE_PREHEAT_FRAC, 1.0) * preheat_mw
df["preheat_delivery_T_C"] = T_CROSSOVER
df["radiant_MWth"] = np.where(decoke, DECOKE_RADIANT_FRAC, 1.0) * radiant_mw
df["radiant_process_T_C"] = T_COT
df["total_MWth"] = df.preheat_MWth + df.radiant_MWth
df = df.round(4)

out = "ethane_cracker_pilot_load_8760.csv"
df.to_csv(out)

# ---- summary ------------------------------------------------------------
print(f"Per tonne ethylene: preheat {preheat_gj_t:.2f} GJ/t, radiant {radiant_gj_t:.2f} GJ/t "
      f"(sensible {radiant_sensible_gj_t:.2f} + reaction {reaction_gj_t:.2f})")
print(f"Design duty: preheat {preheat_mw:.2f} MW, radiant {radiant_mw:.2f} MW, "
      f"total {preheat_mw + radiant_mw:.2f} MWth")
print(f"Decoke hours: {decoke.sum()}  ({decoke.sum() / 8760:.1%} of year)")
print(f"Annual ethylene: {df.ethylene_t_per_h.sum():,.0f} t")
print(f"Annual heat: preheat {df.preheat_MWth.sum():,.0f} MWh, "
      f"radiant {df.radiant_MWth.sum():,.0f} MWh, total {df.total_MWth.sum():,.0f} MWh")
print(f"Wrote {out}")
