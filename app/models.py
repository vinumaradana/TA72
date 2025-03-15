from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class UserSignup(BaseModel):
    name: str
    email: str
    password: str
    location: str

class UserLogin(BaseModel):
    email: str
    password: str

class SensorData(BaseModel):
    value: float
    unit: str
    timestamp: Optional[datetime] = None
    device_id: Optional[str] = None

class WardrobeItem(BaseModel):
    item_name: str
    item_type: str

class Device(BaseModel):
    device_id: str 