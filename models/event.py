from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class Event(BaseModel):
    venue: str
    venue_url: str
    name: str
    date: datetime
    url: Optional[str] = None
    artists: List[str] = Field(default_factory=list)
    price: Optional[str] = None
    description: Optional[str] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
    
    def __hash__(self):
        return hash((self.venue, self.name, self.date.date()))
    
    def __eq__(self, other):
        if not isinstance(other, Event):
            return False
        return (self.venue == other.venue and 
                self.name == other.name and 
                self.date.date() == other.date.date())