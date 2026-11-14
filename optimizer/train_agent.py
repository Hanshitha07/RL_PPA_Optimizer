import argparse
import pandas as pd
from stable_baselines3 import PPO
from stable_baselines3.common.env_checker import check_env
from optimizer.dse_env import HardwareDSEEnv

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True, help="Path to hardware config.yaml")
    parser.add_argument("--steps", type=int, default=300, help="Total RL training steps")
    parser.add_argument("--mock", action="store_true", help="Use fast synthetic physics instead of Vivado")
    args = parser.parse_args()

    env = HardwareDSEEnv(config_path=args.config, mock=args.mock)
    check_env(env)  # Verifies Gymnasium API compliance

    model = PPO("MlpPolicy", env, n_steps=32, batch_size=16, learning_rate=3e-3, verbose=1)
    model.learn(total_timesteps=args.steps)

    # Export all explored hardware points to CSV
    records = list(env.cache.values())
    df = pd.DataFrame(records)
    out_csv = f"results/{env.project_name}_{'mock' if args.mock else 'vivado'}_results.csv"
    df.to_csv(out_csv, index=False)

    # Print best timing-clean configuration
    valid = df[df["wns_ns"] >= 0].copy()
    w = env.cfg["reward_weights"]
    valid["ppa_score"] = (
        w["power"] * (valid["power_mw"] / env.baseline["power_mw"])
        + w["delay"] * (valid["delay_ns"] / env.baseline["delay_ns"])
        + w["area"] * (valid["area_score"] / env.baseline["area_score"])
    )
    best = valid.sort_values("ppa_score").iloc[0]
    print("\n=== BASELINE DESIGN ===")
    print(env.baseline)
    print("\n=== RL-OPTIMIZED DESIGN ===")
    print(best.to_dict())

if __name__ == "__main__":
    main()