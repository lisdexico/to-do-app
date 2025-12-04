from pydantic import BaseModel, Field, model_validator
from typing import Dict, Optional, List
import uuid
from datetime import datetime
from src.models.workitem import WorkItem, WorkItemStatus, WorkItemType

MIN_NAME_LENGTH = 1
MAX_NAME_LENGTH = 255
MIN_DESCRIPTION_LENGTH = 1
MAX_DESCRIPTION_LENGTH = 2000
MAX_WORK_ITEMS_COUNT = 5000


class WorkItemNotFoundError(ValueError):
    """Raised when a work item is not found on the board."""
    pass


class WorkItemRelationshipError(ValueError):
    """Raised when there's an issue with work item relationships."""
    pass


class WorkBoard(BaseModel):
    """ Represents a collection of workitems """
    id: uuid.UUID = Field(default_factory=uuid.uuid4, frozen=True)
    created_at: datetime = Field(default_factory=datetime.now, frozen=True)
    name: str = Field(min_length=MIN_NAME_LENGTH, max_length=MAX_NAME_LENGTH)
    description: str = Field(min_length=MIN_DESCRIPTION_LENGTH, max_length=MAX_DESCRIPTION_LENGTH)
    work_items: Dict[uuid.UUID, WorkItem] = Field(default_factory=dict, max_length=MAX_WORK_ITEMS_COUNT)

    @model_validator(mode='after')
    def validate_work_items_count(self):
        """Validate that the number of work items is less than MAX_WORK_ITEMS_COUNT."""
        if len(self.work_items) > MAX_WORK_ITEMS_COUNT:
            raise ValueError(f"The number of work items must be less than {MAX_WORK_ITEMS_COUNT}")
        return self
    
    # Basic CRUD
    def add_work_item(self, work_item: WorkItem) -> WorkItem:
        """Add a work item to the board."""
        
        # check that the number of work items does not exceed the maximum allowed
        if len(self.work_items) >= MAX_WORK_ITEMS_COUNT:
            raise ValueError(f"The number of work items must be less than {MAX_WORK_ITEMS_COUNT}")

        # add the work item
        self.work_items[work_item.id] = work_item

        # link the work item to the parent if present
        if work_item.parent_id is not None:
            self.link_parent_and_child(work_item.parent_id, work_item.id)

        # link the work item to the children if present
        if work_item.children_ids:
            for child_id in work_item.children_ids:
                self.link_parent_and_child(work_item.id, child_id)
        return work_item

    def find_work_item(self, id: uuid.UUID) -> Optional[WorkItem]:
        """ Return the work item if it exists, otherwise return None """
        return self.work_items.get(id)

    def get_work_item(self, id: uuid.UUID) -> Optional[WorkItem]:
        """ Return the work item if it exists, otherwise raise an error """
        item = self.find_work_item(id)
        if item is None:
            raise WorkItemNotFoundError(f"Work item {id} not found on board")
        return item
    
    def update_work_item(self, id: uuid.UUID, **updates) -> WorkItem:
        item = self.get_work_item(id)
        updated_item = item.model_copy(update=updates)
        self.work_items[id] = updated_item
        return updated_item

    def delete_work_item(self, id: uuid.UUID) -> None:
        """ Delete a work item from the board and all references to it"""
        item = self.get_work_item(id)

        # Remove the reference to this item from its parent
        if item.parent_id is not None:
            self.unlink_parent_and_child(item.parent_id, id)

        # Remove references to this item from its children
        # Make a copy of the list to avoid modification during iteration
        if item.children_ids:
            children_ids_copy = list(item.children_ids)
            for child_id in children_ids_copy:
                self.unlink_parent_and_child(id, child_id)
        del self.work_items[id]
    
    # Query methods
    def list_work_items(self) -> List[WorkItem]:
        return list(self.work_items.values())

    def list_by_type(self, work_item_type: WorkItemType) -> List[WorkItem]:
        return [item for item in self.work_items.values() if item.work_item_type == work_item_type]

    def list_by_status(self, status: WorkItemStatus) -> List[WorkItem]:
        return [item for item in self.work_items.values() if item.status == status]
    
    # Relationship methods
    def link_parent_and_child(self, parent_id: uuid.UUID, child_id: uuid.UUID) -> None:
        """ Link two work items together as parent and child """

        parent = self.get_work_item(parent_id)
        child = self.get_work_item(child_id)
        child.add_parent(parent_id)
        parent.add_child(child_id)


    def unlink_parent_and_child(self, parent_id: uuid.UUID, child_id: uuid.UUID) -> None:
        """ Remove the link between a parent and a child """
        parent = self.get_work_item(parent_id)
        child = self.get_work_item(child_id)
        parent.remove_child(child_id)
        child.remove_parent()
        
    def get_children(self, parent_id: uuid.UUID) -> List[WorkItem]:
        """ Return all the children of a parent """
        parent = self.get_work_item(parent_id)
        return [self.get_work_item(child_id) for child_id in parent.children_ids]
    
    def get_parent(self, child_id: uuid.UUID) -> Optional[WorkItem]:
        """ Return the parent of a child, if it exists, otherwise return None """
        child = self.get_work_item(child_id)
        if child.parent_id is None:
            return None
        return self.get_work_item(child.parent_id)