from fastapi import APIRouter, HTTPException, status
from firebase_admin import auth
import httpx

from app.auth import schemas
from app.core.config import settings
from app.core.security import create_access_token
from app.data.repo import FirestoreRepo

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/register", status_code=status.HTTP_201_CREATED)
def register_user(user_in: schemas.UserCreate):
    """
    Create a new user in Firebase Authentication.
    """
    try:
        user_record = auth.create_user(
            email=user_in.email,
            password=user_in.password
        )
        # Optional: create a user profile document in Firestore
        repo = FirestoreRepo(user_id=user_record.uid)
        repo.db.collection("users").document(user_record.uid).set({
            "email": user_record.email,
            "created_at": user_record.user_metadata.creation_timestamp
        })
        return {"uid": user_record.uid, "email": user_record.email}
    except auth.EmailAlreadyExistsError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The email address is already in use by another account.",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {e}",
        )

@router.post("/login", response_model=schemas.LoginResponse)
async def login_for_access_token(form_data: schemas.UserLogin):
    """
    Logs in a user by verifying their password with Firebase Auth REST API
    and returns a custom JWT access token.
    """
    # The Firebase Admin SDK cannot verify passwords.
    # We must use the Firebase Auth REST API for this.
    rest_api_url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={settings.FIREBASE_API_KEY}"
    
    payload = {
        "email": form_data.email,
        "password": form_data.password,
        "returnSecureToken": True
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(rest_api_url, json=payload)
            response.raise_for_status() # Raise an exception for 4XX or 5XX status codes
            
            data = response.json()
            firebase_uid = data['localId']
            
            # Create our own custom JWT
            access_token = create_access_token(
                data={"sub": firebase_uid} # Use the Firebase UID as the subject of our JWT
            )
            
            # For the LoginResponse schema, we also need the user's email
            # We assume for now that form_data.email is the correct email.
            user_info = schemas.User(uid=firebase_uid, email=form_data.email)
            
            return {
                "access_token": access_token,
                "token_type": "bearer",
                "user": user_info
            }

        except httpx.HTTPStatusError as e:
            # The API returns specific error messages we can parse
            error_detail = e.response.json().get("error", {}).get("message", "Invalid credentials")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=error_detail,
                headers={"WWW-Authenticate": "Bearer"},
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"An unexpected error occurred during login: {e}",
            )

# @router.post("/login", response_model=schemas.Token)
# async def login_for_access_token_real(form_data: schemas.UserLogin):
#     """
#     Logs in a user by verifying their password with Firebase Auth REST API
#     and returns a custom JWT access token.
#     """
#     # The Firebase Admin SDK cannot verify passwords.
#     # We must use the Firebase Auth REST API for this.
#     rest_api_url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={settings.FIREBASE_API_KEY}"
    
#     payload = {
#         "email": form_data.email,
#         "password": form_data.password,
#         "returnSecureToken": True
#     }

#     async with httpx.AsyncClient() as client:
#         try:
#             response = await client.post(rest_api_url, json=payload)
#             response.raise_for_status() # Raise an exception for 4XX or 5XX status codes
            
#             data = response.json()
#             firebase_uid = data['localId']
            
#             # Create our own custom JWT
#             access_token = create_access_token(
#                 data={"sub": firebase_uid} # Use the Firebase UID as the subject of our JWT
#             )
            
#             return {"access_token": access_token, "token_type": "bearer"}

#         except httpx.HTTPStatusError as e:
#             # The API returns specific error messages we can parse
#             error_detail = e.response.json().get("error", {}).get("message", "Invalid credentials")
#             raise HTTPException(
#                 status_code=status.HTTP_401_UNAUTHORIZED,
#                 detail=error_detail,
#                 headers={"WWW-Authenticate": "Bearer"},
#             )
#         except Exception as e:
#             raise HTTPException(
#                 status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#                 detail=f"An unexpected error occurred during login: {e}",
#             )
