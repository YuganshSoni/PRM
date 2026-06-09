from pydantic import BaseModel, EmailStr, Field


class UpdateEmployeeRequest(BaseModel):
    full_name: str = Field(..., min_length=1, max_length=150)
    email: EmailStr
    department: str = Field(..., min_length=1, max_length=100)
    designation: str = Field(..., min_length=1, max_length=100)


class AssignManagerRequest(BaseModel):
    employee_user_id: int = Field(..., ge=1)
    manager_user_id: int = Field(..., ge=1)
