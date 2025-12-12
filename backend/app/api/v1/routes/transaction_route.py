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

router = APIRouter(prefix="/transactions", tags=["Transactions"])

# -----------------------------------------------------------
# CREATE TRANSACTION
# -----------------------------------------------------------
@router.post("")
async def create_transaction(
    request: Request,
    data: TransactionCreate,
    db=Depends(get_database),
    current_user={"id": "test_user_123"}
):
    user_id = current_user["id"]

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

    # UPDATED: Use "category"
    merchant_id = f"MCT-{data.category[:3].upper()}-{user_id[:4]}"

    txn = TransactionModel(
        user_id=user_id,
        amount=data.amount,
        category=data.category,           # UPDATED
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
# GET TRANSACTIONS (WITH FILTERS)
# -----------------------------------------------------------
@router.get("")
async def get_user_transactions(
    request: Request,
    db=Depends(get_database),
    current_user={"id": "test_user_123"},
    from_dt: str | None = None,
    to_dt: str | None = None,
    sort_by: str = "transaction_date",
    desc: bool = True,
    min_amount: float | None = None,
    max_amount: float | None = None,
    category: str | None = None,
    status: str | None = None,
):
    user_id = current_user["id"]

    q = {"user_id": user_id}

    # ---- DATE FILTER ----
    if from_dt or to_dt:
        q["transaction_date"] = {}
        if from_dt:
            q["transaction_date"]["$gte"] = datetime.fromisoformat(from_dt)
        if to_dt:
            q["transaction_date"]["$lte"] = datetime.fromisoformat(to_dt)

    # ---- AMOUNT FILTER ----
    if min_amount is not None or max_amount is not None:
        q["amount"] = {}
        if min_amount is not None:
            q["amount"]["$gte"] = float(min_amount)
        if max_amount is not None:
            q["amount"]["$lte"] = float(max_amount)

    # ---- CATEGORY FILTER ----
    if category and category != "all":
        q["category"] = category      # UPDATED

    # ---- STATUS FILTER ----
    if status and status != "all":
        q["status"] = status

    sort_dir = -1 if desc else 1

    cursor = db.transactions.find(q).sort(sort_by, sort_dir)
    txns = await cursor.to_list(length=300)

    for t in txns:
        t["_id"] = str(t["_id"])

    return {"transactions": txns}
