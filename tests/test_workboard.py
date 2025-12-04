import uuid
from datetime import datetime, timedelta
import pytest
from pydantic import ValidationError

from src.models.workboard import (
    WorkBoard,
    WorkItemNotFoundError,
    WorkItemRelationshipError,
    MAX_WORK_ITEMS_COUNT,
    MAX_NAME_LENGTH,
    MAX_DESCRIPTION_LENGTH,
)
from src.models.workitem import WorkItem, WorkItemStatus, WorkItemType, MAX_CHILDREN_COUNT


def create_sample_board(**overrides) -> WorkBoard:
    """Helper function to create a sample WorkBoard."""
    data = {
        "name": "Test Board",
        "description": "Test description",
    }
    data.update(overrides)
    return WorkBoard(**data)


def create_sample_work_item(**overrides) -> WorkItem:
    """Helper function to create a sample WorkItem."""
    data = {
        "work_item_type": WorkItemType.TASK,
        "title": "Test title",
        "description": "Test description",
    }
    data.update(overrides)
    return WorkItem(**data)


# ==================== Board Creation Tests ====================

class TestWorkBoardCreation:
    def test_board_creation_defaults(self):
        """Test that a WorkBoard is created with default values."""
        board = create_sample_board()
        
        assert isinstance(board.id, uuid.UUID)
        assert board.name == "Test Board"
        assert board.description == "Test description"
        assert board.work_items == {}
        assert isinstance(board.created_at, datetime)
        
        # created_at should be close to "now"
        now = datetime.now()
        assert now - timedelta(seconds=5) <= board.created_at <= now + timedelta(seconds=5)

    def test_board_creation_with_custom_values(self):
        """Test creating a board with custom values."""
        board = WorkBoard(
            name="My Project Board",
            description="A board for managing project tasks"
        )
        
        assert board.name == "My Project Board"
        assert board.description == "A board for managing project tasks"
        assert len(board.work_items) == 0

    def test_board_name_validation(self):
        """Test that board name validation works."""
        # Too short
        with pytest.raises(ValidationError):
            WorkBoard(name="", description="Test")
        
        # Too long
        with pytest.raises(ValidationError):
            WorkBoard(name="x" * (MAX_NAME_LENGTH + 1), description="Test")

    def test_board_description_validation(self):
        """Test that board description validation works."""
        # Too short
        with pytest.raises(ValidationError):
            WorkBoard(name="Test", description="")
        
        # Too long
        with pytest.raises(ValidationError):
            WorkBoard(name="Test", description="x" * (MAX_DESCRIPTION_LENGTH + 1))

    def test_board_frozen_fields(self):
        """Test that frozen fields cannot be modified."""
        board = create_sample_board()
        
        with pytest.raises(ValidationError):
            board.id = uuid.uuid4()
        
        with pytest.raises(ValidationError):
            board.created_at = datetime.now()


# ==================== Work Item CRUD Tests ====================

class TestWorkItemCRUD:
    def test_add_work_item(self):
        """Test adding a work item to the board."""
        board = create_sample_board()
        
        item = create_sample_work_item(
            work_item_type=WorkItemType.TASK,
            title="Test Task",
            description="Test description"
        )
        added_item = board.add_work_item(item)
        
        assert item.id in board.work_items
        assert added_item.title == "Test Task"
        assert added_item.description == "Test description"
        assert added_item.work_item_type == WorkItemType.TASK
        assert added_item.status == WorkItemStatus.TO_DO
        assert board.work_items[item.id] == item

    def test_add_work_item_with_all_fields(self):
        """Test adding a work item with all fields specified."""
        board = create_sample_board()
        
        item = create_sample_work_item(
            work_item_type=WorkItemType.FEATURE,
            title="New Feature",
            description="Feature description",
            status=WorkItemStatus.IN_PROGRESS
        )
        added_item = board.add_work_item(item)
        
        assert added_item.work_item_type == WorkItemType.FEATURE
        assert added_item.status == WorkItemStatus.IN_PROGRESS
        assert added_item.title == "New Feature"
        assert added_item.description == "Feature description"

    def test_add_work_item_with_parent(self):
        """Test adding a work item with a parent."""
        board = create_sample_board()
        
        # Create and add parent
        parent = create_sample_work_item(
            work_item_type=WorkItemType.EPIC,
            title="Parent Epic",
            description="Parent description"
        )
        board.add_work_item(parent)
        
        # Create and add child with parent_id
        child = create_sample_work_item(
            work_item_type=WorkItemType.FEATURE,
            title="Child Feature",
            description="Child description",
            parent_id=parent.id
        )
        board.add_work_item(child)
        
        assert child.parent_id == parent.id
        assert child.id in parent.children_ids

    def test_add_work_item_with_children(self):
        """Test adding a work item with children."""
        board = create_sample_board()
        
        # Create and add children first
        child1 = create_sample_work_item(
            work_item_type=WorkItemType.TASK,
            title="Child 1",
            description="Child 1 description"
        )
        board.add_work_item(child1)
        
        child2 = create_sample_work_item(
            work_item_type=WorkItemType.TASK,
            title="Child 2",
            description="Child 2 description"
        )
        board.add_work_item(child2)
        
        # Create and add parent with children
        parent = create_sample_work_item(
            work_item_type=WorkItemType.STORY,
            title="Parent Story",
            description="Parent description",
            children_ids=[child1.id, child2.id]
        )
        board.add_work_item(parent)
        
        assert len(parent.children_ids) == 2
        assert child1.id in parent.children_ids
        assert child2.id in parent.children_ids
        assert child1.parent_id == parent.id
        assert child2.parent_id == parent.id

    def test_find_work_item_exists(self):
        """Test finding a work item that exists."""
        board = create_sample_board()
        item = create_sample_work_item(
            work_item_type=WorkItemType.TASK,
            title="Test Task",
            description="Test"
        )
        board.add_work_item(item)
        
        found = board.find_work_item(item.id)
        assert found is not None
        assert found.id == item.id
        assert found.title == "Test Task"

    def test_find_work_item_not_exists(self):
        """Test finding a work item that doesn't exist."""
        board = create_sample_board()
        non_existent_id = uuid.uuid4()
        
        found = board.find_work_item(non_existent_id)
        assert found is None

    def test_get_work_item_exists(self):
        """Test getting a work item that exists."""
        board = create_sample_board()
        item = create_sample_work_item(
            work_item_type=WorkItemType.TASK,
            title="Test Task",
            description="Test"
        )
        board.add_work_item(item)
        
        found = board.get_work_item(item.id)
        assert found.id == item.id
        assert found.title == "Test Task"

    def test_get_work_item_not_exists(self):
        """Test getting a work item that doesn't exist raises exception."""
        board = create_sample_board()
        non_existent_id = uuid.uuid4()
        
        with pytest.raises(WorkItemNotFoundError, match="not found on board"):
            board.get_work_item(non_existent_id)

    def test_update_work_item_title(self):
        """Test updating a work item's title."""
        board = create_sample_board()
        item = create_sample_work_item(
            work_item_type=WorkItemType.TASK,
            title="Old Title",
            description="Test"
        )
        board.add_work_item(item)
        
        updated = board.update_work_item(item.id, title="New Title")
        assert updated.title == "New Title"
        assert board.work_items[item.id].title == "New Title"

    def test_update_work_item_description(self):
        """Test updating a work item's description."""
        board = create_sample_board()
        item = create_sample_work_item(
            work_item_type=WorkItemType.TASK,
            title="Test",
            description="Old description"
        )
        board.add_work_item(item)
        
        updated = board.update_work_item(item.id, description="New description")
        assert updated.description == "New description"

    def test_update_work_item_status(self):
        """Test updating a work item's status."""
        board = create_sample_board()
        item = create_sample_work_item(
            work_item_type=WorkItemType.TASK,
            title="Test",
            description="Test"
        )
        board.add_work_item(item)
        
        assert item.status == WorkItemStatus.TO_DO
        updated = board.update_work_item(item.id, status=WorkItemStatus.IN_PROGRESS)
        assert updated.status == WorkItemStatus.IN_PROGRESS

    def test_update_work_item_multiple_fields(self):
        """Test updating multiple fields at once."""
        board = create_sample_board()
        item = create_sample_work_item(
            work_item_type=WorkItemType.TASK,
            title="Old Title",
            description="Old description",
            status=WorkItemStatus.TO_DO
        )
        board.add_work_item(item)
        
        updated = board.update_work_item(
            item.id,
            title="New Title",
            description="New description",
            status=WorkItemStatus.DONE
        )
        
        assert updated.title == "New Title"
        assert updated.description == "New description"
        assert updated.status == WorkItemStatus.DONE

    def test_update_work_item_not_exists(self):
        """Test updating a work item that doesn't exist raises exception."""
        board = create_sample_board()
        non_existent_id = uuid.uuid4()
        
        with pytest.raises(WorkItemNotFoundError):
            board.update_work_item(non_existent_id, title="New Title")

    def test_delete_work_item(self):
        """Test deleting a work item."""
        board = create_sample_board()
        item = create_sample_work_item(
            work_item_type=WorkItemType.TASK,
            title="Test Task",
            description="Test"
        )
        board.add_work_item(item)
        
        assert item.id in board.work_items
        board.delete_work_item(item.id)
        assert item.id not in board.work_items

    def test_delete_work_item_removes_from_parent(self):
        """Test that deleting a work item removes it from parent's children_ids."""
        board = create_sample_board()
        
        parent = create_sample_work_item(
            work_item_type=WorkItemType.STORY,
            title="Parent",
            description="Parent"
        )
        board.add_work_item(parent)
        
        child = create_sample_work_item(
            work_item_type=WorkItemType.TASK,
            title="Child",
            description="Child",
            parent_id=parent.id
        )
        board.add_work_item(child)
        
        assert child.id in parent.children_ids
        board.delete_work_item(child.id)
        assert child.id not in parent.children_ids
        assert child.id not in board.work_items

    def test_delete_work_item_removes_children_relationships(self):
        """Test that deleting a work item removes children's parent_id."""
        board = create_sample_board()
        
        parent = create_sample_work_item(
            work_item_type=WorkItemType.STORY,
            title="Parent",
            description="Parent"
        )
        board.add_work_item(parent)
        
        child1 = create_sample_work_item(
            work_item_type=WorkItemType.TASK,
            title="Child 1",
            description="Child 1",
            parent_id=parent.id
        )
        board.add_work_item(child1)
        
        child2 = create_sample_work_item(
            work_item_type=WorkItemType.TASK,
            title="Child 2",
            description="Child 2",
            parent_id=parent.id
        )
        board.add_work_item(child2)
        
        assert child1.parent_id == parent.id
        assert child2.parent_id == parent.id
        
        board.delete_work_item(parent.id)
        
        # Children should still exist but parent should be removed
        assert child1.id in board.work_items
        assert child2.id in board.work_items
        assert board.work_items[child1.id].parent_id is None
        assert board.work_items[child2.id].parent_id is None

    def test_delete_work_item_not_exists(self):
        """Test deleting a work item that doesn't exist raises exception."""
        board = create_sample_board()
        non_existent_id = uuid.uuid4()
        
        with pytest.raises(WorkItemNotFoundError):
            board.delete_work_item(non_existent_id)


# ==================== Query Methods Tests ====================

class TestWorkItemQueries:
    def test_list_work_items_empty(self):
        """Test listing work items when board is empty."""
        board = create_sample_board()
        items = board.list_work_items()
        assert items == []
        assert len(items) == 0

    def test_list_work_items_multiple(self):
        """Test listing multiple work items."""
        board = create_sample_board()
        
        item1 = create_sample_work_item(
            work_item_type=WorkItemType.TASK,
            title="Task 1",
            description="Task 1"
        )
        board.add_work_item(item1)
        
        item2 = create_sample_work_item(
            work_item_type=WorkItemType.STORY,
            title="Story 1",
            description="Story 1"
        )
        board.add_work_item(item2)
        
        item3 = create_sample_work_item(
            work_item_type=WorkItemType.FEATURE,
            title="Feature 1",
            description="Feature 1"
        )
        board.add_work_item(item3)
        
        items = board.list_work_items()
        assert len(items) == 3
        item_ids = {item.id for item in items}
        assert item_ids == {item1.id, item2.id, item3.id}

    def test_list_by_type(self):
        """Test listing work items by type."""
        board = create_sample_board()
        
        task1 = create_sample_work_item(
            work_item_type=WorkItemType.TASK,
            title="Task 1",
            description="Task 1"
        )
        board.add_work_item(task1)
        
        task2 = create_sample_work_item(
            work_item_type=WorkItemType.TASK,
            title="Task 2",
            description="Task 2"
        )
        board.add_work_item(task2)
        
        story = create_sample_work_item(
            work_item_type=WorkItemType.STORY,
            title="Story 1",
            description="Story 1"
        )
        board.add_work_item(story)
        
        tasks = board.list_by_type(WorkItemType.TASK)
        assert len(tasks) == 2
        task_ids = {task.id for task in tasks}
        assert task_ids == {task1.id, task2.id}
        assert story.id not in task_ids

    def test_list_by_type_empty(self):
        """Test listing by type when no items of that type exist."""
        board = create_sample_board()
        
        item = create_sample_work_item(
            work_item_type=WorkItemType.TASK,
            title="Task",
            description="Task"
        )
        board.add_work_item(item)
        
        features = board.list_by_type(WorkItemType.FEATURE)
        assert features == []

    def test_list_by_status(self):
        """Test listing work items by status."""
        board = create_sample_board()
        
        todo1 = create_sample_work_item(
            work_item_type=WorkItemType.TASK,
            title="Todo 1",
            description="Todo 1"
        )
        board.add_work_item(todo1)
        
        todo2 = create_sample_work_item(
            work_item_type=WorkItemType.TASK,
            title="Todo 2",
            description="Todo 2"
        )
        board.add_work_item(todo2)
        
        # Update one to in_progress
        board.update_work_item(todo2.id, status=WorkItemStatus.IN_PROGRESS)
        
        todo_items = board.list_by_status(WorkItemStatus.TO_DO)
        assert len(todo_items) == 1
        assert todo_items[0].id == todo1.id
        
        in_progress_items = board.list_by_status(WorkItemStatus.IN_PROGRESS)
        assert len(in_progress_items) == 1
        assert in_progress_items[0].id == todo2.id

    def test_list_by_status_empty(self):
        """Test listing by status when no items have that status."""
        board = create_sample_board()
        
        item = create_sample_work_item(
            work_item_type=WorkItemType.TASK,
            title="Task",
            description="Task"
        )
        board.add_work_item(item)
        
        done_items = board.list_by_status(WorkItemStatus.DONE)
        assert done_items == []


# ==================== Relationship Methods Tests ====================

class TestWorkItemRelationships:
    def test_link_parent_and_child(self):
        """Test linking a parent and child."""
        board = create_sample_board()
        
        parent = create_sample_work_item(
            work_item_type=WorkItemType.STORY,
            title="Parent",
            description="Parent"
        )
        board.add_work_item(parent)
        
        child = create_sample_work_item(
            work_item_type=WorkItemType.TASK,
            title="Child",
            description="Child"
        )
        board.add_work_item(child)
        
        board.link_parent_and_child(parent.id, child.id)
        
        assert child.id in parent.children_ids
        assert child.parent_id == parent.id

    def test_link_parent_and_child_parent_not_exists(self):
        """Test linking when parent doesn't exist raises exception."""
        board = create_sample_board()
        
        child = create_sample_work_item(
            work_item_type=WorkItemType.TASK,
            title="Child",
            description="Child"
        )
        board.add_work_item(child)
        
        non_existent_parent_id = uuid.uuid4()
        
        with pytest.raises(WorkItemNotFoundError):
            board.link_parent_and_child(non_existent_parent_id, child.id)

    def test_link_parent_and_child_child_not_exists(self):
        """Test linking when child doesn't exist raises exception."""
        board = create_sample_board()
        
        parent = create_sample_work_item(
            work_item_type=WorkItemType.STORY,
            title="Parent",
            description="Parent"
        )
        board.add_work_item(parent)
        
        non_existent_child_id = uuid.uuid4()
        
        with pytest.raises(WorkItemNotFoundError):
            board.link_parent_and_child(parent.id, non_existent_child_id)

    def test_link_parent_and_child_max_children_limit(self):
        """Test that linking respects the maximum children count limit."""
        board = create_sample_board()
        
        parent = create_sample_work_item(
            work_item_type=WorkItemType.STORY,
            title="Parent",
            description="Parent"
        )
        board.add_work_item(parent)
        
        # Add exactly MAX_CHILDREN_COUNT children - should work
        children = []
        for i in range(MAX_CHILDREN_COUNT):
            child = create_sample_work_item(
                work_item_type=WorkItemType.TASK,
                title=f"Child {i}",
                description=f"Child {i} description"
            )
            board.add_work_item(child)
            board.link_parent_and_child(parent.id, child.id)
            children.append(child)
        
        assert len(parent.children_ids) == MAX_CHILDREN_COUNT
        assert len(board.get_children(parent.id)) == MAX_CHILDREN_COUNT
        
        # Try to add one more child - should raise ValueError
        extra_child = create_sample_work_item(
            work_item_type=WorkItemType.TASK,
            title="Extra Child",
            description="This should fail"
        )
        board.add_work_item(extra_child)
        
        with pytest.raises(ValueError, match=f"must not exceed {MAX_CHILDREN_COUNT}"):
            board.link_parent_and_child(parent.id, extra_child.id)
        
        # Verify the extra child was not added
        assert len(parent.children_ids) == MAX_CHILDREN_COUNT
        assert extra_child.id not in parent.children_ids

    def test_add_work_item_with_children_max_limit(self):
        """Test that adding a work item with children_ids respects the maximum limit."""
        board = create_sample_board()
        
        # Create exactly MAX_CHILDREN_COUNT children
        children = []
        for i in range(MAX_CHILDREN_COUNT):
            child = create_sample_work_item(
                work_item_type=WorkItemType.TASK,
                title=f"Child {i}",
                description=f"Child {i} description"
            )
            board.add_work_item(child)
            children.append(child)
        
        # Create parent with all children - should work
        children_ids = [child.id for child in children]
        parent = create_sample_work_item(
            work_item_type=WorkItemType.STORY,
            title="Parent",
            description="Parent",
            children_ids=children_ids
        )
        board.add_work_item(parent)
        
        assert len(parent.children_ids) == MAX_CHILDREN_COUNT
        
        # Try to add one more child after creation - should fail
        extra_child = create_sample_work_item(
            work_item_type=WorkItemType.TASK,
            title="Extra Child",
            description="This should fail"
        )
        board.add_work_item(extra_child)
        
        with pytest.raises(ValueError, match=f"must not exceed {MAX_CHILDREN_COUNT}"):
            board.link_parent_and_child(parent.id, extra_child.id)

    def test_add_work_item_with_too_many_children_fails(self):
        """Test that adding a work item with more than MAX_CHILDREN_COUNT children_ids fails validation."""
        board = create_sample_board()
        
        # Create MAX_CHILDREN_COUNT + 1 children
        children = []
        for i in range(MAX_CHILDREN_COUNT + 1):
            child = create_sample_work_item(
                work_item_type=WorkItemType.TASK,
                title=f"Child {i}",
                description=f"Child {i} description"
            )
            board.add_work_item(child)
            children.append(child)
        
        # Try to create parent with too many children - should fail at WorkItem creation
        children_ids = [child.id for child in children]
        
        # This should fail because WorkItem has max_length=MAX_CHILDREN_COUNT on children_ids
        with pytest.raises(ValidationError):
            parent = create_sample_work_item(
                work_item_type=WorkItemType.STORY,
                title="Parent",
                description="Parent",
                children_ids=children_ids
            )
            board.add_work_item(parent)

    def test_unlink_parent_and_child(self):
        """Test unlinking a parent and child."""
        board = create_sample_board()
        
        parent = create_sample_work_item(
            work_item_type=WorkItemType.STORY,
            title="Parent",
            description="Parent"
        )
        board.add_work_item(parent)
        
        child = create_sample_work_item(
            work_item_type=WorkItemType.TASK,
            title="Child",
            description="Child",
            parent_id=parent.id
        )
        board.add_work_item(child)
        
        assert child.id in parent.children_ids
        assert child.parent_id == parent.id
        
        board.unlink_parent_and_child(parent.id, child.id)
        
        assert child.id not in parent.children_ids
        assert child.parent_id is None

    def test_unlink_parent_and_child_not_relationship(self):
        """Test unlinking when relationship doesn't exist raises exception."""
        board = create_sample_board()
        
        parent = create_sample_work_item(
            work_item_type=WorkItemType.STORY,
            title="Parent",
            description="Parent"
        )
        board.add_work_item(parent)
        
        child = create_sample_work_item(
            work_item_type=WorkItemType.TASK,
            title="Child",
            description="Child"
        )
        board.add_work_item(child)
        
        # Child is not a child of parent
        with pytest.raises(ValueError, match="is not a child"):
            board.unlink_parent_and_child(parent.id, child.id)

    def test_get_children(self):
        """Test getting all children of a parent."""
        board = create_sample_board()
        
        parent = create_sample_work_item(
            work_item_type=WorkItemType.STORY,
            title="Parent",
            description="Parent"
        )
        board.add_work_item(parent)
        
        child1 = create_sample_work_item(
            work_item_type=WorkItemType.TASK,
            title="Child 1",
            description="Child 1",
            parent_id=parent.id
        )
        board.add_work_item(child1)
        
        child2 = create_sample_work_item(
            work_item_type=WorkItemType.TASK,
            title="Child 2",
            description="Child 2",
            parent_id=parent.id
        )
        board.add_work_item(child2)
        
        children = board.get_children(parent.id)
        assert len(children) == 2
        child_ids = {child.id for child in children}
        assert child_ids == {child1.id, child2.id}

    def test_get_children_empty(self):
        """Test getting children when parent has no children."""
        board = create_sample_board()
        
        parent = create_sample_work_item(
            work_item_type=WorkItemType.STORY,
            title="Parent",
            description="Parent"
        )
        board.add_work_item(parent)
        
        children = board.get_children(parent.id)
        assert children == []

    def test_get_children_parent_not_exists(self):
        """Test getting children when parent doesn't exist raises exception."""
        board = create_sample_board()
        non_existent_id = uuid.uuid4()
        
        with pytest.raises(WorkItemNotFoundError):
            board.get_children(non_existent_id)

    def test_get_parent(self):
        """Test getting the parent of a child."""
        board = create_sample_board()
        
        parent = create_sample_work_item(
            work_item_type=WorkItemType.STORY,
            title="Parent",
            description="Parent"
        )
        board.add_work_item(parent)
        
        child = create_sample_work_item(
            work_item_type=WorkItemType.TASK,
            title="Child",
            description="Child",
            parent_id=parent.id
        )
        board.add_work_item(child)
        
        found_parent = board.get_parent(child.id)
        assert found_parent is not None
        assert found_parent.id == parent.id

    def test_get_parent_no_parent(self):
        """Test getting parent when child has no parent."""
        board = create_sample_board()
        
        child = create_sample_work_item(
            work_item_type=WorkItemType.TASK,
            title="Child",
            description="Child"
        )
        board.add_work_item(child)
        
        found_parent = board.get_parent(child.id)
        assert found_parent is None

    def test_get_parent_child_not_exists(self):
        """Test getting parent when child doesn't exist raises exception."""
        board = create_sample_board()
        non_existent_id = uuid.uuid4()
        
        with pytest.raises(WorkItemNotFoundError):
            board.get_parent(non_existent_id)


# ==================== Validation Tests ====================

class TestWorkBoardValidation:
    def test_max_work_items_validation(self):
        """Test that board validates maximum work items count."""
        board = create_sample_board()
        
        # Create maximum number of items
        for i in range(MAX_WORK_ITEMS_COUNT):
            item = create_sample_work_item(
                work_item_type=WorkItemType.TASK,
                title=f"Task {i}",
                description=f"Task {i} description"
            )
            board.add_work_item(item)
        
        # This should work
        assert len(board.work_items) == MAX_WORK_ITEMS_COUNT
        
        # Creating one more should fail validation
        with pytest.raises(ValueError, match="must be less than"):
            extra_item = create_sample_work_item(
                work_item_type=WorkItemType.TASK,
                title="One too many",
                description="This should fail"
            )
            board.add_work_item(extra_item)


# ==================== Integration Tests ====================

class TestWorkBoardIntegration:
    def test_complete_workflow(self):
        """Test a complete workflow: create epic -> feature -> story -> task."""
        board = create_sample_board()
        
        # Create epic
        epic = create_sample_work_item(
            work_item_type=WorkItemType.EPIC,
            title="User Authentication Epic",
            description="Epic for user authentication"
        )
        board.add_work_item(epic)
        
        # Create feature under epic
        feature = create_sample_work_item(
            work_item_type=WorkItemType.FEATURE,
            title="Login Feature",
            description="Feature for user login",
            parent_id=epic.id
        )
        board.add_work_item(feature)
        
        # Create story under feature
        story = create_sample_work_item(
            work_item_type=WorkItemType.STORY,
            title="Email Login Story",
            description="Story for email login",
            parent_id=feature.id
        )
        board.add_work_item(story)
        
        # Create task under story
        task = create_sample_work_item(
            work_item_type=WorkItemType.TASK,
            title="Implement email validation",
            description="Task to implement email validation",
            parent_id=story.id
        )
        board.add_work_item(task)
        
        # Verify hierarchy
        assert task.parent_id == story.id
        assert story.parent_id == feature.id
        assert feature.parent_id == epic.id
        
        assert task.id in story.children_ids
        assert story.id in feature.children_ids
        assert feature.id in epic.children_ids
        
        # Verify we can query
        all_items = board.list_work_items()
        assert len(all_items) == 4
        
        tasks = board.list_by_type(WorkItemType.TASK)
        assert len(tasks) == 1
        assert tasks[0].id == task.id
        
        # Verify we can get children
        epic_children = board.get_children(epic.id)
        assert len(epic_children) == 1
        assert epic_children[0].id == feature.id
        
        # Verify we can get parent
        task_parent = board.get_parent(task.id)
        assert task_parent is not None
        assert task_parent.id == story.id

    def test_update_and_delete_workflow(self):
        """Test updating and deleting items in a workflow."""
        board = create_sample_board()
        
        # Create items
        parent = create_sample_work_item(
            work_item_type=WorkItemType.STORY,
            title="Parent Story",
            description="Parent"
        )
        board.add_work_item(parent)
        
        child1 = create_sample_work_item(
            work_item_type=WorkItemType.TASK,
            title="Child 1",
            description="Child 1",
            parent_id=parent.id
        )
        board.add_work_item(child1)
        
        child2 = create_sample_work_item(
            work_item_type=WorkItemType.TASK,
            title="Child 2",
            description="Child 2",
            parent_id=parent.id
        )
        board.add_work_item(child2)
        
        # Update parent
        board.update_work_item(parent.id, title="Updated Parent")
        assert board.get_work_item(parent.id).title == "Updated Parent"
        
        # Update child status
        board.update_work_item(child1.id, status=WorkItemStatus.IN_PROGRESS)
        assert board.get_work_item(child1.id).status == WorkItemStatus.IN_PROGRESS
        
        # Delete one child
        board.delete_work_item(child1.id)
        assert child1.id not in board.work_items
        assert child1.id not in parent.children_ids
        
        # Parent and other child should still exist
        assert parent.id in board.work_items
        assert child2.id in board.work_items
        assert child2.parent_id == parent.id
