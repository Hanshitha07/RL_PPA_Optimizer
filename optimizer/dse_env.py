import os
import json
import shutil
import subprocess
import yaml
import numpy as np
import gymnasium as gym
from gymnasium import spaces
from optimizer.report_parser import parse_vivado_reports


class HardwareDSEEnv(gym.Env):
    def __init__(self, config_path: str, mock: bool = False):
        super().__init__()
        with open(config_path, "r") as f:
            self.cfg = yaml.safe_load(f)

        self.mock = mock
        self.project_name = self.cfg["project_name"]
        self.param_names = list(self.cfg["parameters"].keys())
        self.param_choices = [self.cfg["parameters"][k] for k in self.param_names]
        self.clk_choices = self.cfg["clock"]["period_options_ns"]

        # Action space: [param_0_idx, param_1_idx, ..., clk_idx]
        dims = [len(c) for c in self.param_choices] + [len(self.clk_choices)]
        self.action_space = spaces.MultiDiscrete(dims)

        # Observation: action indices + [power_mw, delay_ns, area_score]
        obs_dim = len(dims) + 3
        self.observation_space = spaces.Box(low=-100.0, high=1e5, shape=(obs_dim,), dtype=np.float32)

        mode_tag = "mock" if self.mock else "vivado"
        os.makedirs("results", exist_ok=True)
        self.cache_file = f"results/cache_{self.project_name}_{mode_tag}.json"
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, "r") as f:
                    self.cache = json.load(f)
            except json.JSONDecodeError:
                self.cache = {}
        else:
            self.cache = {}

        # Evaluate middle configuration as baseline reference
        mid_action = [len(c) // 2 for c in self.param_choices] + [len(self.clk_choices) // 2]
        self.baseline = self._evaluate(mid_action)

    def _mock_physics(self, params: dict, clk_period: float) -> dict:
        complexity = sum((i + 1) * (idx + 1) for i, idx in enumerate(params.values()))
        freq_ghz = 1.0 / clk_period
        power_mw = round(15.0 + 4.5 * complexity * (freq_ghz * 10.0), 3)
        delay_ns = round(4.0 + 1.8 * (len(params) * 2 - complexity * 0.35), 3)
        wns_ns = round(clk_period - delay_ns, 3)
        luts = int(120 + 45 * complexity)
        ffs = int(80 + 30 * complexity)
        return {
            "power_mw": float(power_mw),
            "delay_ns": float(delay_ns),
            "wns_ns": float(wns_ns),
            "luts": int(luts),
            "ffs": int(ffs),
            "area_score": float(round(luts + 0.5 * ffs, 2)),
        }

    def _evaluate(self, action) -> dict:
        action_list = [int(x) for x in np.asarray(action).flatten()]
        param_indices = {name: action_list[i] for i, name in enumerate(self.param_names)}
        clk_idx = action_list[-1]
        clk_period = float(self.clk_choices[clk_idx])

        resolved_params = {}
        for i, (name, idx) in enumerate(param_indices.items()):
            val = self.param_choices[i][idx]
            resolved_params[name] = val.item() if isinstance(val, np.generic) else val

        # Use '-' instead of '=' so Windows vivado.bat never splits the path
        key = "_".join([f"{k}-{v}" for k, v in resolved_params.items()] + [f"CLK-{clk_period}"])

        if key in self.cache:
            return self.cache[key]

        if self.mock:
            metrics = self._mock_physics(param_indices, clk_period)
        else:
            out_dir = f"runs/{self.project_name}/{key}"
            os.makedirs(out_dir, exist_ok=True)

            # Format generics cleanly for Tcl (quote strings, leave numbers unquoted)
            tcl_generics = []
            for k, v in resolved_params.items():
                if isinstance(v, str):
                    tcl_generics.append(f'{{{k}="{v}"}}')
                else:
                    tcl_generics.append(f"{{{k}={v}}}")

            rtl_tcl_list = " ".join([f'"{p}"' for p in self.cfg["rtl_files"]])
            params_tcl_path = f"{out_dir}/params.tcl"
            with open(params_tcl_path, "w") as pf:
                pf.write(f'set top_module "{self.cfg["top_module"]}"\n')
                pf.write(f'set fpga_part "{self.cfg["fpga_part"]}"\n')
                pf.write(f'set clk_port "{self.cfg["clock"]["port_name"]}"\n')
                pf.write(f"set clk_period {clk_period}\n")
                pf.write(f"set rtl_files [list {rtl_tcl_list}]\n")
                pf.write(f"set generics_list [list {' '.join(tcl_generics)}]\n")

            vivado_exe = shutil.which("vivado") or r"C:\AMDDesignTools\2025.2.1\Vivado\bin\vivado.bat"
            cmd = [
                vivado_exe, "-mode", "batch", "-notrace",
                "-source", "optimizer/run_vivado.tcl",
                "-tclargs", out_dir,
            ]
            subprocess.run(cmd, check=True)
            metrics = parse_vivado_reports(out_dir, clk_period)

        metrics["config_key"] = key
        metrics["params"] = resolved_params
        metrics["clk_period_ns"] = clk_period
        self.cache[key] = metrics

        with open(self.cache_file, "w") as f:
            json.dump(
                self.cache,
                f,
                indent=2,
                default=lambda o: o.item() if isinstance(o, np.generic) else str(o),
            )

        return metrics

    def step(self, action):
        action_list = [int(x) for x in np.asarray(action).flatten()]
        m = self._evaluate(action_list)
        w = self.cfg["reward_weights"]
        ppa_cost = (
            w["power"] * (m["power_mw"] / self.baseline["power_mw"])
            + w["delay"] * (m["delay_ns"] / self.baseline["delay_ns"])
            + w["area"] * (m["area_score"] / self.baseline["area_score"])
        )
        # Heavy penalty if circuit fails setup timing (WNS < 0)
        timing_penalty = 2.5 * abs(m["wns_ns"]) if m["wns_ns"] < 0 else 0.0
        reward = -(ppa_cost + timing_penalty)

        obs = np.array(
            action_list + [m["power_mw"], m["delay_ns"], m["area_score"]], dtype=np.float32
        )
        return obs, float(reward), True, False, m

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        init_action = [len(c) // 2 for c in self.param_choices] + [len(self.clk_choices) // 2]
        m = self._evaluate(init_action)
        obs = np.array(
            init_action + [m["power_mw"], m["delay_ns"], m["area_score"]], dtype=np.float32
        )
        return obs, {}