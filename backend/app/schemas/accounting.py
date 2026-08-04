from datetime import datetime, timezone
from typing import List, Literal, Optional
from pydantic import BaseModel, Field, model_validator

# 與 app.services.fs_defs.ACCOUNT_TYPES 同步（M1-1.4：補 cost/other_*/tax）
ACCOUNT_TYPE_LITERAL = Literal[
    "asset", "liability", "equity", "revenue", "cost", "expense",
    "other_income", "other_expense", "tax",
]


class AccountCreate(BaseModel):
    code: str = Field(..., min_length=1)
    name: str = Field(..., min_length=1)
    account_type: ACCOUNT_TYPE_LITERAL
    parent_id: Optional[str] = None
    is_debit_normal: bool = True
    # v006 (M1)：三大報表行（值域白名單在 service 層驗證）
    fs_line: Optional[str] = None


class AccountUpdate(BaseModel):
    code: Optional[str] = None
    name: Optional[str] = None
    account_type: Optional[ACCOUNT_TYPE_LITERAL] = None
    parent_id: Optional[str] = None
    is_debit_normal: Optional[bool] = None
    fs_line: Optional[str] = None
    is_active: Optional[bool] = None


class AccountResponse(BaseModel):
    id: str
    code: str
    name: str
    account_type: str
    is_debit_normal: bool
    is_active: bool
    fs_line: Optional[str] = None
    is_system: bool = False

    class Config:
        from_attributes = True


class JournalLineCreate(BaseModel):
    account_id: str
    debit: float = 0
    credit: float = 0
    description: Optional[str] = None
    reference: Optional[str] = None

    @model_validator(mode="after")
    def check_not_both_zero(self) -> "JournalLineCreate":
        if self.debit == 0 and self.credit == 0:
            raise ValueError("借貸雙方不能同時為零")
        return self


class JournalEntryCreate(BaseModel):
    entry_date: Optional[datetime] = Field(
        default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None)
    )
    source_type: Optional[str] = None
    source_id: Optional[str] = None
    description: Optional[str] = None
    period: Optional[str] = None
    lines: List[JournalLineCreate]


class JournalLineResponse(BaseModel):
    id: str
    account_id: str
    line_no: int
    debit: float
    credit: float
    description: Optional[str] = None

    class Config:
        from_attributes = True


class JournalEntryResponse(BaseModel):
    id: str
    entry_no: str
    entry_date: datetime
    period: Optional[str] = None
    status: str
    description: Optional[str] = None
    lines: List[JournalLineResponse] = []

    class Config:
        from_attributes = True


class ARCreate(BaseModel):
    customer_id: str
    invoice_no: str
    invoice_date: datetime
    due_date: datetime
    amount: float = Field(..., gt=0)


class ARResponse(BaseModel):
    id: str
    customer_id: str
    invoice_no: str
    invoice_date: datetime
    due_date: datetime
    amount: float
    paid_amount: float
    status: str
    aging_days: int

    class Config:
        from_attributes = True
