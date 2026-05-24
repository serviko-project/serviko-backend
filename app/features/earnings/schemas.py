from typing import List
from pydantic import BaseModel, Field

class GraphDataPoint(BaseModel):
    label: str
    value: float

class TransactionResponse(BaseModel):
    id: str
    title: str
    date_str: str
    amount: float
    is_credit: bool

class EarningsSummaryResponse(BaseModel):
    available_balance: float
    period_label: str
    period_earnings: float
    filter: str
    graph_data: List[GraphDataPoint]
    recent_transactions: List[TransactionResponse]

class CashOutRequest(BaseModel):
    amount: float = Field(..., gt=0)
    upi_id: str = Field(..., min_length=3)

class CashOutResponse(BaseModel):
    status: str
    message: str
    withdrawal_id: str
