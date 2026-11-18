from datetime import datetime
from typing import Dict, Any, List, Optional
import time

from backend.vision_simulator import simulate_waste_detection


class AgentState:
    def __init__(self, request_id: int, room: str, item_description: str, priority: str = "Normal", robot_id: int = 1):
        self.request_id = request_id
        self.room = room
        self.item_description = item_description
        self.priority = priority
        self.robot_id = robot_id
        self.status = "INITIALIZING"
        self.target_compartment: Optional[str] = None
        self.needs_human_review = False
        self.human_review_reason = ""
        self.assigned_robot = "BIONEX-AMR-01"
        self.route_path: List[str] = []
        self.estimated_eta = "Arriving at collection point"
        self.vision_data: Dict[str, Any] = {}
        self.safety_passed = False
        self.interlock_status = "LOCKED"
        self.traces: List[Dict[str, Any]] = []

    def add_trace(self, agent_name: str, stage: str, status: str, thought: str, action: str):
        self.traces.append({
            "agent": agent_name,
            "stage": stage,
            "status": status,
            "thought": thought,
            "action": action,
            "timestamp": datetime.now().strftime("%H:%M:%S")
        })

    def to_dict(self) -> dict:
        return {
            "request_id": self.request_id,
            "room": self.room,
            "item_description": self.item_description,
            "priority": self.priority,
            "status": self.status,
            "target_compartment": self.target_compartment,
            "needs_human_review": self.needs_human_review,
            "human_review_reason": self.human_review_reason,
            "assigned_robot": self.assigned_robot,
            "route_path": self.route_path,
            "estimated_eta": self.estimated_eta,
            "vision_data": self.vision_data,
            "safety_passed": self.safety_passed,
            "interlock_status": self.interlock_status,
            "traces": self.traces
        }


class CollectionAgent:
    """Agent 1: Validates collection requests, checks ward parameters, creates tasks."""
    @staticmethod
    def process(state: AgentState, robot_state: dict) -> AgentState:
        state.status = "COLLECTION_EVALUATED"
        
        thought = (
            f"Analyzing collection request #{state.request_id} for {state.room}. "
            f"Item: '{state.item_description}'. Priority: '{state.priority}'. "
            f"AMR Battery: {robot_state.get('battery_percent', 90)}%."
        )
        action = f"Validated task payload. Assigned to AMR Unit {state.robot_id}."
        
        state.add_trace(
            agent_name="Collection Agent",
            stage="Request Validation & Intake",
            status="SUCCESS",
            thought=thought,
            action=action
        )
        return state


class RouteEmergencyAgent:
    """Agent 2: Prioritizes emergency requests, manages waypoints, requests route planning."""
    @staticmethod
    def process(state: AgentState, robot_state: dict) -> AgentState:
        battery = robot_state.get("battery_percent", 90)
        
        if battery < 20:
            state.needs_human_review = True
            state.human_review_reason = f"Robot battery critically low ({battery}%). Rerouted to charging dock."
            state.status = "REROUTED_TO_DOCK"
            state.add_trace(
                agent_name="Route/Emergency Agent",
                stage="Corridor Route Planning",
                status="DIVERTED",
                thought=f"Battery at {battery}% is below 20% safe threshold. Cannot service task safely.",
                action="Diverted AMR to Central Docking Bay for immediate contact charging."
            )
            return state

        # Check Emergency Priority
        if state.priority.upper() == "EMERGENCY":
            state.route_path = ["Emergency Express Corridor", "Trauma Bay Transit", f"Arrival at {state.room}"]
            state.estimated_eta = "High-speed emergency transit (< 2 mins)"
            thought = (
                "EMERGENCY REQUEST DETECTED: Preempting all routine corridor sweeps. "
                "Engaging high-priority audio-visual warning beacons and Nav2 priority route."
            )
            action = f"Dispatched express navigation corridor directly to {state.room}."
        elif state.priority.upper() == "HIGH":
            state.route_path = ["Main Wing Corridor", "Service Elevator A", f"Arrival at {state.room}"]
            state.estimated_eta = "Expedited transit (< 4 mins)"
            thought = "High-priority request: Assigned expedited corridor slot."
            action = f"Navigating to {state.room} via service elevator."
        else:
            state.route_path = ["Hospital Central Corridor", "Ward Concourse", f"Arrival at {state.room}"]
            state.estimated_eta = "Standard routine transit (< 6 mins)"
            thought = "Routine ward collection: Standard waypoint path selected."
            action = f"Scheduled standard transit to {state.room}."

        state.status = "EN_ROUTE_TO_WARD"
        state.add_trace(
            agent_name="Route/Emergency Agent",
            stage="Corridor Route Planning",
            status="DISPATCHED",
            thought=thought,
            action=action
        )
        return state


class SegregationAgent:
    """Agent 3: Evaluates vision camera output, checks CPCB rules, sends uncertain items for human review."""
    @staticmethod
    def process(state: AgentState, vision_output: Optional[dict] = None) -> AgentState:
        if not vision_output:
            vision_output = simulate_waste_detection(item_text=state.item_description)

        state.vision_data = vision_output
        confidence = vision_output.get("confidence", 0.0)
        is_mixed = vision_output.get("is_mixed", False)
        is_leaking = vision_output.get("is_leaking", False)
        category = vision_output.get("category", "Human Review")

        # Crucial Safety Rule:
        # If waste is mixed, unidentified, leaking, entangled, or confidence < 85% -> HALT MANIPULATION
        if is_mixed or is_leaking or confidence < 0.85 or category == "Human Review":
            state.needs_human_review = True
            state.human_review_reason = (
                f"Classification uncertain (Confidence: {int(confidence*100)}%) or mixed/leaking material detected. "
                "Robotic arm halted to prevent contamination and puncture incidents."
            )
            state.status = "HUMAN_REVIEW_REQUIRED"
            state.target_compartment = "Human Review"
            state.interlock_status = "SAFETY_HALT"
            
            thought = (
                f"VISION WARNING: Detected '{vision_output.get('detected_class')}' (Confidence: {int(confidence*100)}%). "
                f"Mixed status: {is_mixed}, Leaking: {is_leaking}. Under BioNex Safety Protocol Section 10, robot MUST NOT force-separate."
            )
            action = "Robotic arm locked in safe standby position. Broadcasted 'Human Review Required' alert to nursing station."
            
            state.add_trace(
                agent_name="Segregation Agent",
                stage="AI Vision & Rule Verification",
                status="FLAGGED_FOR_HUMAN",
                thought=thought,
                action=action
            )
            return state

        # Safe and validated
        state.target_compartment = category
        state.safety_passed = True
        state.status = "SEGREGATION_APPROVED"
        
        thought = (
            f"Vision model identified '{vision_output.get('detected_class')}' with {int(confidence*100)}% confidence. "
            f"Deterministic CPCB 2016 validation: Safe and eligible for {category.upper()} Compartment."
        )
        action = f"Authorized robotic arm pick & place into {category.upper()} sealed gate."
        
        state.add_trace(
            agent_name="Segregation Agent",
            stage="AI Vision & Rule Verification",
            status="APPROVED",
            thought=thought,
            action=action
        )
        return state


class MonitoringAgent:
    """Agent 4: Monitors battery, bins, obstacles, system health, and triggers hardware interlocks."""
    @staticmethod
    def process(state: AgentState, bin_levels: dict, robot_state: dict) -> AgentState:
        target_cat = state.target_compartment
        if target_cat in bin_levels:
            current_fill = bin_levels[target_cat]
            if current_fill >= 80:
                state.needs_human_review = True
                state.human_review_reason = f"{target_cat} bin is {current_fill}% full (>= 80% safety limit). Cannot deposit."
                state.status = "BIN_FULL_HALT"
                state.interlock_status = "INTERLOCK_LOCKED"
                
                state.add_trace(
                    agent_name="Monitoring Agent",
                    stage="Telemetry & Hardware Interlock",
                    status="BIN_FULL_ALERT",
                    thought=f"Target compartment {target_cat} is at {current_fill}% capacity, exceeding the 80% hospital safety limit.",
                    action="Gate opening inhibited. Generated 'Bin Full' sanitation alert."
                )
                return state

        if robot_state.get("e_stop_active", 0) == 1:
            state.status = "E_STOP_ENGAGED"
            state.interlock_status = "E_STOP_DISCONNECT"
            state.add_trace(
                agent_name="Monitoring Agent",
                stage="Telemetry & Hardware Interlock",
                status="E_STOP_ENGAGED",
                thought="Physical Emergency Stop button is engaged on the AMR chassis.",
                action="Hardware actuator relay de-energized. All mechanical motions disabled."
            )
            return state

        if state.safety_passed and not state.needs_human_review:
            state.status = "DEPOSIT_COMPLETED"
            state.interlock_status = f"{target_cat.upper()}_GATE_OPENED_AND_SEALED"
            
            thought = (
                f"Hardware watchdog: Obstacle radar clear (3.2m), Battery {robot_state.get('battery_percent', 90)}%, "
                f"Target bin {target_cat} at {bin_levels.get(target_cat, 35)}% capacity. All interlocks verified."
            )
            action = (
                f"Opened {target_cat.upper()} compartment gate via PCA9685 servo CH_{target_cat[:1]}. "
                "Verified deposit via internal infrared sensor. Sealed gate securely."
            )
            
            state.add_trace(
                agent_name="Monitoring Agent",
                stage="Telemetry & Hardware Interlock",
                status="COMPLETED",
                thought=thought,
                action=action
            )
        return state


class AgenticWorkflowOrchestrator:
    """
    Coordinates multi-agent LangGraph-style state graph execution.
    Passes state sequentially through Collection -> Route -> Segregation -> Monitoring.
    """
    @staticmethod
    def run_pipeline(request_id: int, room: str, item_description: str, priority: str = "Normal",
                     vision_output: Optional[dict] = None, robot_state: Optional[dict] = None,
                     bin_levels: Optional[dict] = None) -> Dict[str, Any]:
        
        if not robot_state:
            robot_state = {"battery_percent": 92, "current_location": "Ward A Station", "e_stop_active": 0}
        if not bin_levels:
            bin_levels = {"Yellow": 35, "Red": 50, "White": 20, "Blue": 15}

        state = AgentState(request_id, room, item_description, priority)

        state = CollectionAgent.process(state, robot_state)
        state = RouteEmergencyAgent.process(state, robot_state)
        if state.status == "REROUTED_TO_DOCK":
            return state.to_dict()

        state = SegregationAgent.process(state, vision_output)
        state = MonitoringAgent.process(state, bin_levels, robot_state)

        return state.to_dict()
