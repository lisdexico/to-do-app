from pydantic import BaseModel, Field, model_validator
from typing import Optional, List
from enum import Enum
import uuid
from datetime import datetime

MIN_TITLE_LENGTH = 1
MAX_TITLE_LENGTH = 255
MIN_DESCRIPTION_LENGTH = 1
MAX_DESCRIPTION_LENGTH = 2000
MAX_CHILDREN_COUNT = 100

class WorkItemStatus(str, Enum):
    TO_DO = "to_do"
    IN_PROGRESS = "in_progress"
    DONE = "done"

class WorkItemType(str, Enum):
    TASK = "task"
    STORY = "story"
    FEATURE = "feature"
    EPIC = "epic"

class WorkItem(BaseModel):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, frozen=True)
    work_item_type: WorkItemType = Field(frozen=True)
    created_at: datetime = Field(default_factory=datetime.now, frozen=True)
    parent_id: Optional[uuid.UUID] = Field(default=None)
    children_ids: List[uuid.UUID] = Field(default_factory=list, max_length=MAX_CHILDREN_COUNT)
    status: WorkItemStatus = Field(default=WorkItemStatus.TO_DO)
    title: str = Field(min_length=MIN_TITLE_LENGTH, max_length=MAX_TITLE_LENGTH)
    description: str = Field(min_length=MIN_DESCRIPTION_LENGTH, max_length=MAX_DESCRIPTION_LENGTH)

    @model_validator(mode='after')
    def validate_children_ids_uniqueness(self):
        """Validate that children_ids contains only unique UUIDs."""
        if len(self.children_ids) != len(set(self.children_ids)):
            raise ValueError("children_ids must contain unique UUIDs")
        return self

    def start(self) -> None:
        self.status = WorkItemStatus.IN_PROGRESS

    def complete(self) -> None:
        self.status = WorkItemStatus.DONE 
    
    def reset(self) -> None:
        self.status = WorkItemStatus.TO_DO

    def __str__(self) -> str:
        return f"{self.work_item_type.value} {self.title}"

    def __repr__(self) -> str:
        return f"<WorkItem {self.id} {self.work_item_type.value} {self.title}>"