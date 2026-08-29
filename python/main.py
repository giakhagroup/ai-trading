import uvicorn
from fastapi import FastAPI, HTTPException
from typing import Dict, Any, List
import logging

from models import CanonicalCandle, CandidateSignal, ValidatedSignal, RejectedSignal
from strategies.rsi_breakout import RSIBreakoutStrategy
from risk.risk_engine import RiskEngine

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("QuantEngine")

app = FastAPI(title="AI Trading Python Quant & Risk Engine", version="2.0.0")

# Initialize Engine Components
strategies = [RSIBreakoutStrategy(rsi_oversold=35.0, rsi_overbought=70.0)]
risk_engine = RiskEngine(min_rr=1.5, allow_lunch_trades=False)

# In-memory signal audit log
candidate_signals: List[CandidateSignal] = []
validated_signals: List[ValidatedSignal] = []
rejected_signals: List[RejectedSignal] = []

@app.get("/health")
def health():
    return {
        "status": "online",
        "strategies": [s.name for s in strategies],
        "risk_engine": "active"
    }

@app.post("/events/candle")
def on_candle_event(candle: CanonicalCandle):
    """
    Receives Canonical Candle stream (with TradingView indicators) from Node.js Gateway.
    Executes Strategy pipeline -> Candidate Signals -> Risk Engine -> Validated Signals.
    """
    logger.info(f"Received candle: {candle.internal_symbol} {candle.timeframe} Close={candle.close} Indicators={candle.indicators}")
    
    results = {
        "candidates": [],
        "validated": [],
        "rejected": []
    }

    # 1. Run through Strategies
    for strategy in strategies:
        candidate = strategy.evaluate(candle)
        if candidate:
            logger.info(f"Generated Candidate Signal: {candidate.signal_id} by {strategy.name} on {candidate.symbol}")
            candidate_signals.append(candidate)
            results["candidates"].append(candidate.model_dump())

            # 2. Evaluate via Risk Engine
            session = candle.session_type or SessionType.CONTINUOUS
            decision = risk_engine.validate(candidate, current_session=session)

            if isinstance(decision, ValidatedSignal):
                logger.info(f"✅ VALIDATED Signal: {candidate.signal_id} (R:R={decision.risk_reward_ratio})")
                validated_signals.append(decision)
                results["validated"].append(decision.model_dump())
            else:
                logger.warning(f"❌ REJECTED Signal: {candidate.signal_id} - Reasons: {decision.rejection_reasons}")
                rejected_signals.append(decision)
                results["rejected"].append(decision.model_dump())

    return results

@app.get("/signals/validated")
def get_validated_signals():
    return validated_signals

@app.get("/signals/rejected")
def get_rejected_signals():
    return rejected_signals

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
