# GOVERNANCE PHASE 1 — LOCKED (v5.2). Do not modify without explicit approval.
from enum import Enum, auto

class GovernanceState(Enum):
    INIT = "INIT"
    SANITY_OK = "SANITY_OK"
    DOD_OK = "DOD_OK"
    ARMED = "ARMED"
    DRY_RUN = "DRY_RUN"
    EXECUTING = "EXECUTING"
    RECONCILED = "RECONCILED" # Post-Cycle
    HALTED = "HALTED"
    SLEEP = "SLEEP"

class GovernanceError(Exception):
    pass

class GovernanceStateMachine:
    def __init__(self):
        self.current_state = GovernanceState.INIT
        self.transitions = {
            GovernanceState.INIT: [GovernanceState.SANITY_OK, GovernanceState.HALTED],
            GovernanceState.SANITY_OK: [GovernanceState.DOD_OK, GovernanceState.HALTED],
            GovernanceState.DOD_OK: [GovernanceState.ARMED, GovernanceState.HALTED],
            GovernanceState.ARMED: [GovernanceState.DRY_RUN, GovernanceState.EXECUTING, GovernanceState.HALTED],
            GovernanceState.DRY_RUN: [GovernanceState.RECONCILED, GovernanceState.HALTED],
            GovernanceState.EXECUTING: [GovernanceState.RECONCILED, GovernanceState.HALTED],
            GovernanceState.RECONCILED: [GovernanceState.SLEEP, GovernanceState.HALTED],
            GovernanceState.HALTED: [], # Terminal
            GovernanceState.SLEEP: []   # Terminal for this process
        }
        
    def transition(self, to_state: GovernanceState, meta: dict = None):
        if to_state not in self.transitions[self.current_state]:
            raise GovernanceError(f"Invalid transition: {self.current_state} -> {to_state}")
        
        self.current_state = to_state
        return {"old": self.current_state, "new": to_state, "meta": meta}
