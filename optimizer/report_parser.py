import re


def parse_vivado_reports(out_dir: str, clk_period: float) -> dict:
    with open(f"{out_dir}/timing.rpt", "r") as f:
        timing_txt = f.read()

    # Match actual numeric WNS value below the dashed separator line
    wns_match = re.search(
        r"WNS\(ns\)\s+TNS\(ns\).*?[-]+\s+[-]+\s*\n\s*(-?\d+\.\d+)",
        timing_txt,
        re.S,
    )
    wns = float(wns_match.group(1)) if wns_match else -5.0
    critical_delay = round(clk_period - wns, 4)

    with open(f"{out_dir}/util.rpt", "r") as f:
        util_txt = f.read()
    lut_match = re.search(r"Slice LUTs\*?\s*\|\s*(\d+)", util_txt)
    ff_match = re.search(r"Slice Registers\s*\|\s*(\d+)", util_txt)
    luts = int(lut_match.group(1)) if lut_match else 9999
    ffs = int(ff_match.group(1)) if ff_match else 9999

    with open(f"{out_dir}/power.rpt", "r") as f:
        power_txt = f.read()
    pwr_match = re.search(r"Dynamic \(W\)\s*\|\s*(\d+\.\d+)", power_txt)
    dyn_power_mw = round(float(pwr_match.group(1)) * 1000.0, 3) if pwr_match else 999.0

    return {
        "power_mw": dyn_power_mw,
        "delay_ns": critical_delay,
        "wns_ns": wns,
        "luts": luts,
        "ffs": ffs,
        "area_score": round(luts + 0.5 * ffs, 2),
    }