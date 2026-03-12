from __future__ import annotations

from pydantic import BaseModel, Field


class DailyKPI(BaseModel):
    new_leads: int = 0
    active_dialogs: int = 0
    incoming_messages: int = 0
    outgoing_messages: int = 0
    new_dialogs: int = 0
    meaningful_conversations: int = 0
    target_actions: int = 0
    lost_leads: int = 0
    handoff_to_human: int = 0
    followup_returns: int = 0


class FunnelMetrics(BaseModel):
    leads_by_stage: dict[str, int] = Field(default_factory=dict)
    stage_transitions: dict[str, int] = Field(default_factory=dict)
    stuck_leads_by_stage: dict[str, int] = Field(default_factory=dict)
    avg_stage_dwell_hours: dict[str, float] = Field(default_factory=dict)
    overall_conversion_rate: float = 0.0
    step_conversion_rates: dict[str, float] = Field(default_factory=dict)
    dropoff_points: dict[str, int] = Field(default_factory=dict)


class IntentMetrics(BaseModel):
    intent_distribution: dict[str, int] = Field(default_factory=dict)
    top_question_categories: dict[str, int] = Field(default_factory=dict)
    top_objection_categories: dict[str, int] = Field(default_factory=dict)
    top_services: dict[str, int] = Field(default_factory=dict)
    price_questions: int = 0
    objections: int = 0
    unclear_cases: int = 0
    booking_intents: int = 0
    contact_sharing_intents: int = 0
    ghosted_leads: int = 0
    human_handoff_dialogs: int = 0
    loss_reasons: dict[str, int] = Field(default_factory=dict)


class QualityMetrics(BaseModel):
    low_confidence_rate: float = 0.0
    no_next_step_rate: float = 0.0
    no_meaningful_progress_rate: float = 0.0
    handoff_rate: float = 0.0
    followup_return_rate: float = 0.0
    avg_dialog_length_messages: float = 0.0
    avg_messages_per_lead: float = 0.0
    avg_time_to_key_action_hours: float = 0.0
    avg_time_first_message_to_booking_hours: float = 0.0


class InsightBlock(BaseModel):
    key_findings: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    risk_flags: list[str] = Field(default_factory=list)
    llm_summary: str | None = None


class ChartArtifact(BaseModel):
    chart_name: str
    file_path: str


class DailyAnalyticsReport(BaseModel):
    report_date: str
    timezone: str
    kpi: DailyKPI
    funnel: FunnelMetrics
    intents: IntentMetrics
    quality: QualityMetrics
    insights: InsightBlock
    charts: list[ChartArtifact] = Field(default_factory=list)
