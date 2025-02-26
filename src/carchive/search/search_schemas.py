# carchive2/src/carchive2/search/search_schemas.py
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import datetime

class MetaFilterSchema(BaseModel):
    key: str
    value: Any

class AdvancedSearchCriteria(BaseModel):
    text_query: Optional[str] = Field(None, description="Substring to match in message content.")
    conversation_title_query: Optional[str] = Field(None, description="Substring to match in conversation title.")
    date_after: Optional[datetime.datetime] = None
    date_before: Optional[datetime.datetime] = None
    meta_filters: Optional[List[MetaFilterSchema]] = None
    limit: int = 50
