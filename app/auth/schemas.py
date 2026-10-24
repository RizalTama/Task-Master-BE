from pydantic import BaseModel, EmailStr

class UserCreate(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class TokenData(BaseModel):
    uid: str | None = None

class User(BaseModel):
    uid: str
    email: EmailStr

class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: User

class UserInDB(BaseModel):
    uid: str
    email: EmailStr

class UserLogin(BaseModel):
    email: EmailStr
    password: str
