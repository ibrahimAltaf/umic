"""Matter and entity Pydantic schemas."""

from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class MatterTypeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    code: str
    name: str


class MatterStatusOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    code: str
    name: str
    is_closed: bool


class BillingClassificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    code: str
    name: str
    allows_proposed_billing: bool


class MatterCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    matter_type_code: str
    status_code: str = "open"
    billing_classification_code: str = "requires_review"
    claim_number: Optional[str] = None
    policy_number: Optional[str] = None
    case_number: Optional[str] = None
    appraisal_number: Optional[str] = None
    property_address: Optional[str] = None
    date_of_loss: Optional[date] = None
    date_of_discovery: Optional[date] = None
    open_date: Optional[date] = None
    hourly_rate: Optional[Decimal] = None
    billing_method: Optional[str] = None
    is_confidential: bool = False
    is_privileged: bool = False
    is_personal: bool = False
    notes: Optional[str] = None
    search_keywords: Optional[str] = None
    aliases: List[str] = Field(default_factory=list)


class MatterUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    status_code: Optional[str] = None
    billing_classification_code: Optional[str] = None
    claim_number: Optional[str] = None
    policy_number: Optional[str] = None
    case_number: Optional[str] = None
    appraisal_number: Optional[str] = None
    property_address: Optional[str] = None
    date_of_loss: Optional[date] = None
    date_of_discovery: Optional[date] = None
    open_date: Optional[date] = None
    closed_date: Optional[date] = None
    hourly_rate: Optional[Decimal] = None
    billing_method: Optional[str] = None
    is_confidential: Optional[bool] = None
    is_privileged: Optional[bool] = None
    is_personal: Optional[bool] = None
    notes: Optional[str] = None
    search_keywords: Optional[str] = None
    dropbox_folder_link: Optional[str] = None
    google_drive_folder_link: Optional[str] = None
    time_expense_sheet_link: Optional[str] = None


class MatterOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    matter_number: str
    name: str
    claim_number: Optional[str] = None
    policy_number: Optional[str] = None
    case_number: Optional[str] = None
    appraisal_number: Optional[str] = None
    property_address: Optional[str] = None
    date_of_loss: Optional[date] = None
    open_date: Optional[date] = None
    closed_date: Optional[date] = None
    hourly_rate: Optional[Decimal] = None
    billing_method: Optional[str] = None
    is_confidential: bool
    is_privileged: bool
    is_personal: bool
    notes: Optional[str] = None
    created_at: datetime
    matter_type: MatterTypeOut
    status: MatterStatusOut
    billing_classification: BillingClassificationOut
    aliases: List[str] = []


class EntityTypeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    code: str
    name: str
    category: str


class EntityCreate(BaseModel):
    entity_type_code: str
    legal_name: str = Field(..., min_length=1, max_length=255)
    display_name: Optional[str] = None
    primary_email: Optional[str] = None
    primary_phone: Optional[str] = None
    primary_domain: Optional[str] = None
    notes: Optional[str] = None
    aliases: List[str] = Field(default_factory=list)


class EntityUpdate(BaseModel):
    legal_name: Optional[str] = None
    display_name: Optional[str] = None
    primary_email: Optional[str] = None
    primary_phone: Optional[str] = None
    primary_domain: Optional[str] = None
    notes: Optional[str] = None
    status: Optional[str] = None


class EntityOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    legal_name: str
    display_name: str
    status: str
    primary_email: Optional[str] = None
    primary_phone: Optional[str] = None
    primary_domain: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime
    entity_type: EntityTypeOut
    aliases: List[str] = []


class RelationshipCreate(BaseModel):
    matter_id: UUID
    entity_id: UUID
    role: str = Field(..., min_length=1, max_length=64)
    organization_represented: Optional[str] = None
    is_primary: bool = False
    source: Optional[str] = "manual"
    confidence: Optional[str] = "user"
    is_user_approved: bool = True
    notes: Optional[str] = None


class RelationshipOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    matter_id: UUID
    entity_id: UUID
    role: str
    organization_represented: Optional[str] = None
    is_primary: bool
    source: Optional[str] = None
    confidence: Optional[str] = None
    is_user_approved: bool
    notes: Optional[str] = None
    matter_name: Optional[str] = None
    entity_name: Optional[str] = None


class ReviewItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    item_type: str
    priority: str
    status: str
    title: str
    explanation: Optional[str] = None
    suggested_action: Optional[str] = None
    matter_id: Optional[UUID] = None
    kanban_column: str
    created_at: datetime


class ReviewItemUpdate(BaseModel):
    status: Optional[str] = None
    kanban_column: Optional[str] = None
    resolution: Optional[str] = None
    assigned_user_id: Optional[UUID] = None


class BillingEntryCreate(BaseModel):
    matter_id: UUID
    activity_date: date
    description: str
    details: Optional[str] = None
    code: Optional[str] = None
    library_code: Optional[str] = "general"
    time_charge: Optional[Decimal] = None
    mileage: Optional[Decimal] = None
    cost_incurred: Optional[Decimal] = None
    hourly_rate: Optional[Decimal] = None
    notes: Optional[str] = None
    is_manual_override: bool = True


class BillingEntryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    matter_id: UUID
    activity_date: date
    description: str
    details: Optional[str] = None
    time_charge: Optional[Decimal] = None
    mileage: Optional[Decimal] = None
    cost_incurred: Optional[Decimal] = None
    hourly_rate: Optional[Decimal] = None
    time_amount: Optional[Decimal] = None
    total_amount: Optional[Decimal] = None
    billing_status: str
    approval_status: str
    invoice_status: str
    created_at: datetime
    matter_name: Optional[str] = None
    code: Optional[str] = None


class BillingEntryDecision(BaseModel):
    reason: Optional[str] = None


class DashboardStats(BaseModel):
    active_matters: int
    personal_matters: int
    billable_matters: int
    open_review_items: int
    pending_billing_entries: int
    approved_billing_total: Decimal
    entities_count: int
    integrations_connected: int
    matters_by_status: list[dict]
    billing_by_month: list[dict]
    review_by_column: list[dict]


class AuditEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    timestamp: datetime
    action: str
    actor_type: str
    actor_user_id: Optional[UUID] = None
    record_type: Optional[str] = None
    record_id: Optional[UUID] = None
    matter_id: Optional[UUID] = None
    reason: Optional[str] = None
    source: Optional[str] = None


class IntegrationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    provider: str
    account_label: str
    status: str
    last_successful_sync_at: Optional[datetime] = None
    last_failed_sync_at: Optional[datetime] = None
    last_error: Optional[str] = None
