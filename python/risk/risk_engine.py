from typing import Union, List
from models import (
    CandidateSignal,
    ValidatedSignal,
    RejectedSignal,
    SignalDirection,
    SessionType,
    RiskDecision
)

class RiskEngine:
    """
    V2.0-024: Risk Engine Boundary
    Enforces risk filters before a candidate signal is validated:
    - R:R ratio check (e.g. >= 1.5)
    - Session filter (e.g. reject ATO, ATC, or LUNCH if prohibited)
    - Stop-loss validity check (SL must be on correct side of Entry)
    - Max risk per trade
    """
    def __init__(self, min_rr: float = 1.5, allow_lunch_trades: bool = False, max_loss_pct: float = 0.07):
        self.min_rr = min_rr
        self.allow_lunch_trades = allow_lunch_trades
        self.max_loss_pct = max_loss_pct

    def validate(
        self,
        candidate: CandidateSignal,
        current_session: SessionType = SessionType.CONTINUOUS
    ) -> Union[ValidatedSignal, RejectedSignal]:
        rejections: List[str] = []

        # 1. Check Session
        if not self.allow_lunch_trades and current_session == SessionType.LUNCH:
            rejections.append("Session is LUNCH: Trading suspended during lunch break")
        if current_session in [SessionType.ATO, SessionType.ATC]:
            rejections.append(f"Session is {current_session.value}: Direct algorithmic entry restricted during auction call")

        # 2. Check Direction & StopLoss logic
        entry = candidate.entry_price
        sl = candidate.stop_loss
        tp = candidate.take_profit

        if candidate.direction == SignalDirection.LONG:
            if sl >= entry:
                rejections.append("Invalid LONG: Stop Loss must be lower than Entry price")
            if tp <= entry:
                rejections.append("Invalid LONG: Take Profit must be higher than Entry price")
            
            risk = entry - sl
            reward = tp - entry
        else: # SHORT
            if sl <= entry:
                rejections.append("Invalid SHORT: Stop Loss must be higher than Entry price")
            if tp >= entry:
                rejections.append("Invalid SHORT: Take Profit must be lower than Entry price")

            risk = sl - entry
            reward = entry - tp

        # 3. Check Risk:Reward ratio
        if risk <= 0:
            rejections.append("Calculated risk is <= 0")
            rr_ratio = 0.0
        else:
            rr_ratio = reward / risk
            if rr_ratio < self.min_rr:
                rejections.append(f"R:R ratio ({rr_ratio:.2f}) is lower than minimum required ({self.min_rr:.2f})")

        # 4. Check Maximum Stop Loss %
        if entry > 0:
            loss_pct = risk / entry
            if loss_pct > self.max_loss_pct:
                rejections.append(f"Stop Loss distance ({loss_pct*100:.2f}%) exceeds maximum allowable risk limit ({self.max_loss_pct*100:.2f}%)")

        # Final decision
        if rejections:
            return RejectedSignal(
                signal=candidate,
                rejection_reasons=rejections
            )

        return ValidatedSignal(
            signal=candidate,
            decision=RiskDecision.APPROVE,
            risk_score=1.0,
            risk_reward_ratio=round(rr_ratio, 2),
            notes=["Passed all standard risk boundaries (R:R, Session, MaxLoss)"]
        )
