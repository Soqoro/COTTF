from __future__ import annotations
import os, json, time, argparse, datetime as dt
from pathlib import Path
from dotenv import load_dotenv

from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.default_config import DEFAULT_CONFIG

load_dotenv()

def daterange(start: str, end: str, stride_days: int = 1):
    d = dt.date.fromisoformat(start)
    E = dt.date.fromisoformat(end)
    while d <= E:
        yield d.isoformat()
        d += dt.timedelta(days=stride_days)


def save_row(run_dir: Path, row: dict):
    (run_dir/"episodes.ndjson").open("a", encoding="utf-8").write(json.dumps(row)+"\n")

def main(cfg_path: str):
    cfg = json.loads(Path(cfg_path).read_text())
    results_dir = Path(os.getenv("TRADINGAGENTS_RESULTS_DIR","experiments/results"))
    run_dir = results_dir / cfg["run_id"]; run_dir.mkdir(parents=True, exist_ok=True)

    pkg_cfg = DEFAULT_CONFIG.copy()
    pkg_cfg["llm_provider"]   = cfg["llm"]["provider"]
    pkg_cfg["deep_think_llm"] = cfg["llm"]["deep"]
    pkg_cfg["quick_think_llm"]= cfg["llm"]["quick"]
    pkg_cfg["online_tools"]   = cfg.get("online_tools", True)

    ta = TradingAgentsGraph(
        debug=False,
        config=pkg_cfg,
        selected_analysts=cfg["analysts"]
    )

    for tkr in cfg["tickers"]:
        for d in daterange(**cfg["dates"]):
            try:
                t0 = time.time()
                state, decision = ta.propagate(tkr, d)
                dur = time.time() - t0
                row = {
                    "run_id": cfg["run_id"],
                    "ticker": tkr, "date": d,
                    "decision": decision,
                    "market_report": state.get("market_report",""),
                    "news_report": state.get("news_report",""),
                    "social_report": state.get("sentiment_report",""),
                    "fund_report": state.get("fundamentals_report",""),
                    "invest_history": state.get("investment_debate_state",{}).get("history",""),
                    "trader_plan": state.get("trader_investment_decision",""),
                    "risk_history": state.get("risk_debate_state",{}).get("history",""),
                    "risk_decision": state.get("final_trade_decision",""),
                    "duration_s": dur
                }
                save_row(run_dir, row)
            except Exception as e:
                print(f"[WARN] {tkr} {d} failed: {e}")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    args = ap.parse_args()
    main(args.config)
