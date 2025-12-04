from pydantic import BaseModel

class TransactionCreate(BaseModel):
    amount: float
    transaction_type: str
    channel: str
