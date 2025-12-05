# from fastapi import Depends, HTTPException
# from fastapi.core.security import OAuth2PasswordBearer
# from app.core.security import SECRET_KEY, ALGORITHM
# import jwt

# oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")

# def get_current_user(token: str = Depends(oauth2_scheme)):
#     try:
#         payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
#         user_id: str = payload.get("id")

#         if user_id is None:
#             raise HTTPException(status_code=401, detail="Invalid token")

#         return user_id

#     except jwt.ExpiredSignatureError:
#         raise HTTPException(status_code=401, detail="Token expired")

#     except jwt.InvalidTokenError:
#         raise HTTPException(status_code=401, detail="Invalid token")




# app/core/auth.py

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from app.core.security import decode_access_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


# -----------------------------
# EXTRACT CURRENT USER FROM JWT
# -----------------------------
def get_current_user(token: str = Depends(oauth2_scheme)):
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing"
        )

    decoded = decode_access_token(token)

    # Ensure token contains user id
    if "id" not in decoded:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload"
        )

    return decoded
