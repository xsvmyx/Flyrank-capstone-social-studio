from pydantic import BaseModel, EmailStr

class RegisterCredentials(BaseModel):
    email: str
    password: str
    first_name: str
    last_name: str

