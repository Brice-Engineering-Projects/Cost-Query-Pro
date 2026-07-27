"""src/cost_query_pro/schemas/agent.py"""

from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class SearchParameters(BaseModel):
    """Structured search criteria extracted from a user's natural language question.

    Returned by the LLM in Step 1 of the secure query pipeline.
    The backend uses these to build and execute database queries — the LLM
    never accesses the database directly.
    """

    model_config = ConfigDict(extra="ignore")

    intent: Literal["cost_search"] = Field(
        ..., description="Query intent — always 'cost_search' for this pipeline."
    )
    item: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Item description keyword extracted from the question.",
        examples=["24-inch ductile iron pipe"],
    )
    state: str = Field(
        ...,
        min_length=2,
        max_length=2,
        description="Two-letter US state code.",
        examples=["FL"],
    )
    year_start: int = Field(
        ...,
        ge=1900,
        le=2100,
        description="Start of the year range (inclusive).",
    )
    year_end: int = Field(
        ...,
        ge=1900,
        le=2100,
        description="End of the year range (inclusive).",
    )
    unit: Optional[str] = Field(
        None,
        max_length=50,
        description="Unit of measure, if specified (e.g., 'LF', 'EA').",
    )
    price_min: Optional[float] = Field(
        None,
        ge=0,
        description="Minimum unit price filter, if specified.",
    )
    price_max: Optional[float] = Field(
        None,
        ge=0,
        description="Maximum unit price filter, if specified.",
    )


class AgentQueryRequest(BaseModel):
    """Incoming request body for the agent query endpoint."""

    question: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="Natural language question from the user.",
        examples=[
            "What have Florida utilities been paying for 24-inch ductile iron pipe over the last five years?"
        ],
    )
    request_id: Optional[str] = Field(
        None,
        description="Optional caller-supplied ID for log correlation.",
    )


class CostSummary(BaseModel):
    """Aggregated statistics returned by the analytics layer (Step 3).

    Only this summary — never raw records — is passed to the LLM for response generation.
    """

    record_count: int = Field(..., description="Number of matching records.")
    median_price: float = Field(
        ..., description="Median unit price across matching records."
    )
    average_price: float = Field(
        ..., description="Mean unit price across matching records."
    )
    minimum_price: float = Field(
        ..., description="Lowest unit price in matching records."
    )
    maximum_price: float = Field(
        ..., description="Highest unit price in matching records."
    )


class ProjectSummary(BaseModel):
    """Project-level metadata returned by the project_lookup tool.

    Covers scope of matching projects without exposing individual project records.
    """

    project_count: int = Field(
        ..., description="Number of distinct projects matching the search."
    )
    year_min: int = Field(..., description="Earliest project year in matching results.")
    year_max: int = Field(..., description="Latest project year in matching results.")
    states: list[str] = Field(
        ..., description="Distinct state codes covered by matching projects."
    )


class SearchScopeOut(BaseModel):
    """Search parameters used to retrieve the data backing the answer.

    Returned to the caller as the verifiable citation for the LLM's response.
    Contains only search metadata — no individual project records.
    """

    item: str
    state: str
    year_start: int
    year_end: int
    unit: Optional[str] = None
    price_min: Optional[float] = None
    price_max: Optional[float] = None


class AgentQueryResponse(BaseModel):
    """Response from POST /api/v1/agent/query."""

    answer: str = Field(..., description="Natural-language answer from the LLM.")
    record_count: int = Field(
        ..., description="Number of DB records used to generate the answer."
    )
    search_scope: SearchScopeOut = Field(
        ..., description="Search parameters used — the verifiable data citation."
    )
    provider: str = Field(
        ..., description="LLM provider used: 'claude', 'openai', or 'fallback'."
    )
    model: str = Field(..., description="Model identifier (e.g. 'claude-sonnet-4-6').")
    request_id: str = Field(..., description="ID for log correlation.")
