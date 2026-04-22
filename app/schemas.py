from typing import Literal, Optional
from pydantic import BaseModel, Field

IntentType = Literal[
    "run_simulation",
    "list_all_parameters",
    "list_parameters_by_keyword",
    "list_all_kpis",
    "list_kpis_by_keyword",
    "query_current_value",
    "query_average_value",
    "explain_variable",
    "explain_impact",
    "query_target_needed",
    "real_world_query",
    "methodology_query",
    "help",
]

class ParameterChange(BaseModel):
    param_phrase: str
    operation: Literal["set", "delta"] = "set"
    value: float

class GoalSeekRequest(BaseModel):
    target_kpi_phrase: str = ""
    target_direction: Literal["increase", "decrease", "reach"] = "reach"
    target_percent_change: Optional[float] = None
    candidate_parameter_phrase: str = ""
    candidate_operation: Literal["set", "delta"] = "delta"
    search_min: Optional[float] = None
    search_max: Optional[float] = None
    steps: int = 21

class UserIntent(BaseModel):
    intent_type: IntentType
    requested_kpis: list[str] = Field(default_factory=list)
    parameter_changes: list[ParameterChange] = Field(default_factory=list)
    keyword: Optional[str] = None
    focus_variable_phrase: Optional[str] = None
    year_start: Optional[int] = None
    year_end: Optional[int] = None
    need_equation: bool = False
    explanation_language: str = "mn"
    goal_seek: Optional[GoalSeekRequest] = None

class MatchCandidate(BaseModel):
    real_name: str
    py_name: Optional[str] = None
    type: str
    units: Optional[str] = None
    comment: Optional[str] = None
    confidence: float

class MatchDecision(BaseModel):
    phrase: str
    status: Literal["matched", "needs_confirmation", "not_found"]
    selected: Optional[str] = None
    selected_py_name: Optional[str] = None
    candidates: list[MatchCandidate] = Field(default_factory=list)

class MatchDecisionList(BaseModel):
    decisions: list[MatchDecision] = Field(default_factory=list)

class RankedEntity(BaseModel):
    real_name: str
    py_name: Optional[str] = None
    type: str
    units: Optional[str] = None
    comment: Optional[str] = None
    relevance_score: float

class RankedEntityList(BaseModel):
    items: list[RankedEntity] = Field(default_factory=list)
