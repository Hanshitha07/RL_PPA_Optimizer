# RL-PPA-Optimizer: Reinforcement Learning Framework for FPGA Design Space Exploration

An automated, hardware-agnostic **Design Space Exploration (DSE)** engine that uses **Proximal Policy Optimization (PPO)** to co-optimize **Power, Performance, and Area (PPA)** for parameterized Verilog HDL designs on Xilinx/AMD FPGAs.

Instead of manually sweeping micro-architectural parameters and clock constraints, the RL agent interacts directly with **AMD Vivado (Batch Mode)** via parameterized Tcl flows, parses post-route timing, utilization, and power reports, and converges toward Pareto-optimal hardware configurations while strictly enforcing setup timing closure ($\text{WNS} \ge 0$).

---

## Key Features

- **Hardware-Agnostic YAML Interface:** Plug in any parameterized Verilog design by defining top-level parameters, clock period candidates, target FPGA part, and PPA reward weights in a `config.yaml` file—zero changes to the RL engine required.
- **Closed-Loop Vivado EDA Integration:** Automatically generates per-configuration Tcl parameter scripts (`params.tcl`) and XDC timing constraints, executes `synth_design`, `opt_design`, `place_design`, and `route_design` in headless batch mode, and extracts post-route metrics (`WNS`, Critical Path Delay, Dynamic Power, Slice LUTs, Flip-Flops).
- **Timing-Aware Multi-Objective Reward Function:** Balances normalized Dynamic Power, Critical Path Delay, and Area Score while applying a steep penalty whenever Worst Negative Slack ($\text{WNS} < 0$) violates setup timing.
- **Persistent Evaluation Cache:** Stores synthesized design points in JSON (`results/cache_<project>_vivado.json`) and CSV logs so redundant EDA runs are skipped instantaneously ($O(1)$ lookup) and interrupted runs resume seamlessly.
- **Fast Mock Physics Mode (`--mock`):** Includes an analytical PPA trade-off simulator to verify RL convergence and reward shaping in seconds before launching full Vivado runs.

---

## System Architecture

```text
+-------------------------------------------------------------------+
|                   PPO RL Agent (Stable-Baselines3)                |
|        Selects Architectural Parameters + Target Clock Period     |
+---------------------------------+---------------------------------+
                                  | Action Vector [p_0, ..., clk_idx]
                                  v
+-------------------------------------------------------------------+
|              Gymnasium Environment (optimizer/dse_env.py)         |
|  1. Checks persistent JSON evaluation cache                       |
|  2. Writes isolated params.tcl & XDC clock constraints            |
|  3. Invokes Vivado Batch Mode (optimizer/run_vivado.tcl)          |
+---------------------------------+---------------------------------+
                                  | Post-Route Reports
                                  v
+-------------------------------------------------------------------+
|              EDA Report Parser (optimizer/report_parser.py)       |
|   Parses timing.rpt, util.rpt, power.rpt -> Computes PPA Reward   |
+-------------------------------------------------------------------+
