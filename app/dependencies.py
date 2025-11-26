from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from app.utils.auth import verify_token
from app.schemas.auth import TokenData

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


def get_current_user(token: str = Depends(oauth2_scheme)):
    """Used on protected endpoints to check it has a valid authorization header"""
    # The OAuth2PasswordBearer dependency checks the authorization header
    # (expects format 'Authorization: Bearer <JWT>') and
    # - if found: returns raw JWT
    # - if not found: raises HTTPException (401 Not authenticated)
    # with response header 'WWW-Authenticate: Bearer'
    payload = verify_token(token)
    username: str = payload.get("sub")
    if username is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
        )
    return TokenData(username=username)
