from pydantic import BaseModel, EmailStr

class LoginCredentials(BaseModel):
    email: str
    password: str