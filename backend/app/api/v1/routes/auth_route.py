from fastapi import APIRouter, HTTPException, Depends
from app.schemas.user_schema import UserSignup, UserLogin, TokenResponse
from app.core.security import hash_password, verify_password, create_access_token
from app.db.mongodb import get_database

router = APIRouter()

@router.post("/signup")
async def signup(user: UserSignup, db=Depends(get_database)):

    existing_user = await db["users"].find_one({"email": user.email})
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    user_data = user.model_dump()
    user_data["password"] = hash_password(user.password)

    result = await db["users"].insert_one(user_data)

    return {
        "status": "success",
        "message": "User registered successfully",
        "user_id": str(result.inserted_id)
    }


@router.post("/login", response_model=TokenResponse)
async def login(credentials: UserLogin, db=Depends(get_database)):

    user = await db["users"].find_one({"email": credentials.email})
    if not user:
        raise HTTPException(status_code=400, detail="Invalid email or password")

    if not verify_password(credentials.password, user["password"]):
        raise HTTPException(status_code=400, detail="Invalid email or password")

    token = create_access_token({"id": str(user["_id"]), "email": user["email"]})

    return TokenResponse(access_token=token)
