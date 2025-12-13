from fastapi import APIRouter, Depends, Request
from datetime import datetime
from app.db.mongodb import get_database
from app.schemas.transaction_schema import TransactionCreate
from app.db.models.transaction_model import TransactionModel
from app.utils.geoip_utils import get_location_from_ip
from app.utils.ip_utils import get_client_ip
from app.utils.device_utils import get_device_id
from app.api.v1.routes.anomaly_route import handle_anomaly
from app.core.dsa.redis_dsa import push_recent_txn
from app.core.auth import get_current_user  # <-- JWT token
# or: from app.api.v1.routes.auth_route import get_current_user

router = APIRouter(prefix="/transactions", tags=["Transactions"])


# -----------------------------------------------------------
# CREATE TRANSACTION USING JWT TOKEN
# -----------------------------------------------------------
@router.post("")
async def create_transaction(
    request: Request,
    data: TransactionCreate,
    db=Depends(get_database),
    current_user=Depends(get_current_user)   # <-- TOKEN REQUIRED
):
    user_id = current_user["id"]  # <- Extract from token

    ip_address = get_client_ip(request)
    device_id = get_device_id(request)
    location = get_location_from_ip(ip_address)

    last_txn = await db.transactions.find_one(
        {"user_id": user_id}, sort=[("_id", -1)]
    )

    previous_txn_date = None
    if last_txn:
        prev = last_txn.get("transaction_date")
        previous_txn_date = datetime.fromisoformat(prev) if isinstance(prev, str) else prev

    transaction_duration = (
        (datetime.utcnow() - previous_txn_date).total_seconds()
        if previous_txn_date else None
    )

    merchant_id = f"MCT-{data.category[:3].upper()}-{user_id[:4]}"

    txn = TransactionModel(
        user_id=user_id,
        amount=data.amount,
        category=data.category,
        description=data.description,
        ip=ip_address,
        device_id=device_id,
        location=location,
        merchant_id=merchant_id,
        transaction_duration=transaction_duration,
        previous_transaction_date=previous_txn_date
    )

    await db.transactions.insert_one(txn.model_dump())

    push_recent_txn(user_id, txn.model_dump(mode="json"))

    await handle_anomaly({
        "is_anomaly": False,
        "event_type": "transaction",
        "event_data": txn.model_dump(mode="json")
    }, db)

    return {"message": "Transaction added", "data": txn.model_dump(mode="json")}


# -----------------------------------------------------------
# GET TRANSACTIONS USING JWT TOKEN
# -----------------------------------------------------------
@router.get("")
async def get_user_transactions(
    request: Request,
    db=Depends(get_database),
    current_user=Depends(get_current_user),   # <-- TOKEN REQUIRED
    from_dt: str | None = None,
    to_dt: str | None = None,
    sort_by: str = "transaction_date",
    desc: bool = True,
    min_amount: float | None = None,
    max_amount: float | None = None,
    category: str | None = None,
    status: str | None = None,
):
    user_id = current_user["id"]  # <-- Extract from token
