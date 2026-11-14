import pandas as pd
import matplotlib.pyplot as plt

benchmarks = [
    {
        "name": "Sobel Edge Detection Accelerator",
        "csv": "results/sobel_edge_accelerator_vivado_results.csv",
        "out_png": "results/sobel_pareto_plot.png",
        "base_key": "RAM_STYLE-distributed_GRAD_WIDTH-10_APPROX_MODE-1_PIPE_STAGES-2_CLK-10.0",
    },
    {
        "name": "Pipelined 4-Tap FIR Filter",
        "csv": "results/pipelined_fir_filter_vivado_results.csv",
        "out_png": "results/fir_pareto_plot.png",
        "base_key": "DATA_WIDTH-12_PIPE_EN-1_APPROX_COEFF-0_CLK-10.0",
    },
]

for b in benchmarks:
    df = pd.read_csv(b["csv"])
    valid = df[df["wns_ns"] >= 0].copy()

    base_rows = df[df["config_key"] == b["base_key"]]
    base = base_rows.iloc[0] if not base_rows.empty else df.iloc[0]

    valid["ppa_score"] = (
        0.40 * (valid["power_mw"] / base["power_mw"])
        + 0.35 * (valid["delay_ns"] / base["delay_ns"])
        + 0.25 * (valid["area_score"] / base["area_score"])
    )
    best = valid.sort_values("ppa_score").iloc[0]

    print(f"\n=== {b['name']} ===")
    print(f"Baseline: Power={base['power_mw']} mW | Delay={base['delay_ns']} ns | Area={base['area_score']} | WNS={base['wns_ns']} ns")
    print(f"Optimal : Power={best['power_mw']} mW | Delay={best['delay_ns']} ns | Area={best['area_score']} | WNS={best['wns_ns']} ns")
    print(f"Config  : {best['config_key']}")

    plt.figure(figsize=(8, 5))
    sc = plt.scatter(
        valid["delay_ns"],
        valid["power_mw"],
        c=valid["luts"],
        cmap="viridis",
        s=90,
        alpha=0.85,
        edgecolors="k",
        label="Explored Valid Designs",
    )
    plt.colorbar(sc, label="Slice LUTs (Area)")
    plt.scatter(base["delay_ns"], base["power_mw"], color="red", marker="X", s=200, label=f"Baseline ({base['power_mw']} mW)")
    plt.scatter(best["delay_ns"], best["power_mw"], color="lime", edgecolors="black", marker="*", s=300, label=f"RL-Optimal ({best['power_mw']} mW)")

    plt.title(f"RL-PPA Design Space Exploration: {b['name']}")
    plt.xlabel("Critical Path Delay (ns)")
    plt.ylabel("Dynamic Power (mW)")
    plt.grid(True, linestyle="--", alpha=0.5)
    plt.legend()
    plt.tight_layout()
    plt.savefig(b["out_png"], dpi=300)
    print(f"Saved {b['out_png']}")