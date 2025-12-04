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
    MAX_CHILDREN_COUNT,
)
from src.models.workitem import WorkItem, WorkItemStatus, WorkItemType


def create_sample_board(**overrides) -> WorkBoard:
    """Helper function to create a sample WorkBoard."""
    data = {
        "name": "Test Board",
        "description": "Test description",
    }
    data.update(overrides)
    return WorkBoard(**data)


# ==================== Board Creation Tests ====================

def test_board_creation_defaults():
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


def test_board_creation_with_custom_values():
    """Test creating a board with custom values."""
    board = WorkBoard(
        name="My Project Board",
        description="A board for managing project tasks"
    )
    
    assert board.name == "My Project Board"
    assert board.description == "A board for managing project tasks"
    assert len(board.work_items) == 0


def test_board_name_validation():
    """Test that board name validation works."""
    # Too short
    with pytest.raises(ValidationError):
        WorkBoard(name="", description="Test")
    
    # Too long
    with pytest.raises(ValidationError):
        WorkBoard(name="x" * (MAX_NAME_LENGTH + 1), description="Test")


def test_board_description_validation():
    """Test that board description validation works."""
    # Too short
    with pytest.raises(ValidationError):
        WorkBoard(name="Test", description="")
    
    # Too long
    with pytest.raises(ValidationError):
        WorkBoard(name="Test", description="x" * (MAX_DESCRIPTION_LENGTH + 1))


def test_board_frozen_fields():
    """Test that frozen fields cannot be modified."""
    board = create_sample_board()
    
    with pytest.raises(ValidationError):
        board.id = uuid.uuid4()
    
    with pytest.raises(ValidationError):
        board.created_at = datetime.now()


# ==================== Work Item Creation Tests ====================

def test_create_work_item():
    """Test creating a work item on the board."""
    board = create_sample_board()
    
    item = board.create_work_item(
        work_item_type=WorkItemType.TASK,
        title="Test Task",
        description="Test description"
    )
    
    assert item.id in board.work_items
    assert item.title == "Test Task"
    assert item.description == "Test description"
    assert item.work_item_type == WorkItemType.TASK
    assert item.status == WorkItemStatus.TO_DO
    assert board.work_items[item.id] == item


def test_create_work_item_with_all_fields():
    """Test creating a work item with all fields specified."""
    board = create_sample_board()
    
    item = board.create_work_item(
        work_item_type=WorkItemType.FEATURE,
        title="New Feature",
        description="Feature description",
        status=WorkItemStatus.IN_PROGRESS
    )
    
    assert item.work_item_type == WorkItemType.FEATURE
    assert item.status == WorkItemStatus.IN_PROGRESS
    assert item.title == "New Feature"
    assert item.description == "Feature description"


def test_create_work_item_with_parent():
    """Test creating a work item with a parent."""
    board = create_sample_board()
    
    # Create parent
    parent = board.create_work_item(
        work_item_type=WorkItemType.EPIC,
        title="Parent Epic",
        description="Parent description"
    )
    
    # Create child
    child = board.create_work_item(
        work_item_type=WorkItemType.FEATURE,
        title="Child Feature",
        description="Child description",
        parent_id=parent.id
    )
    
    assert child.parent_id == parent.id
    assert child.id in parent.children_ids


def test_create_work_item_with_children():
    """Test creating a work item with children."""
    board = create_sample_board()
    
    # Create children first
    child1 = board.create_work_item(
        work_item_type=WorkItemType.TASK,
        title="Child 1",
        description="Child 1 description"
    )
    child2 = board.create_work_item(
        work_item_type=WorkItemType.TASK,
        title="Child 2",
        description="Child 2 description"
    )
    
    # Create parent with children
    parent = board.create_work_item(
        work_item_type=WorkItemType.STORY,
        title="Parent Story",
        description="Parent description",
        children_ids=[child1.id, child2.id]
    )
    
    assert len(parent.children_ids) == 2
    assert child1.id in parent.children_ids
    assert child2.id in parent.children_ids
    assert child1.parent_id == parent.id
    assert child2.parent_id == parent.id


# ==================== Work Item Retrieval Tests ====================

def test_find_work_item_exists():
    """Test finding a work item that exists."""
    board = create_sample_board()
    item = board.create_work_item(
        work_item_type=WorkItemType.TASK,
        title="Test Task",
        description="Test"
    )
    
    found = board.find_work_item(item.id)
    assert found is not None
    assert found.id == item.id
    assert found.title == "Test Task"


def test_find_work_item_not_exists():
    """Test finding a work item that doesn't exist."""
    board = create_sample_board()
    non_existent_id = uuid.uuid4()
    
    found = board.find_work_item(non_existent_id)
    assert found is None


def test_get_work_item_exists():
    """Test getting a work item that exists."""
    board = create_sample_board()
    item = board.create_work_item(
        work_item_type=WorkItemType.TASK,
        title="Test Task",
        description="Test"
    )
    
    found = board.get_work_item(item.id)
    assert found.id == item.id
    assert found.title == "Test Task"


def test_get_work_item_not_exists():
    """Test getting a work item that doesn't exist raises exception."""
    board = create_sample_board()
    non_existent_id = uuid.uuid4()
    
    with pytest.raises(WorkItemNotFoundError, match="not found on board"):
        board.get_work_item(non_existent_id)


# ==================== Work Item Update Tests ====================

def test_update_work_item_title():
    """Test updating a work item's title."""
    board = create_sample_board()
    item = board.create_work_item(
        work_item_type=WorkItemType.TASK,
        title="Old Title",
        description="Test"
    )
    
    updated = board.update_work_item(item.id, title="New Title")
    assert updated.title == "New Title"
    assert board.work_items[item.id].title == "New Title"


def test_update_work_item_description():
    """Test updating a work item's description."""
    board = create_sample_board()
    item = board.create_work_item(
        work_item_type=WorkItemType.TASK,
        title="Test",
        description="Old description"
    )
    
    updated = board.update_work_item(item.id, description="New description")
    assert updated.description == "New description"


def test_update_work_item_status():
    """Test updating a work item's status."""
    board = create_sample_board()
    item = board.create_work_item(
        work_item_type=WorkItemType.TASK,
        title="Test",
        description="Test"
    )
    
    assert item.status == WorkItemStatus.TO_DO
    updated = board.update_work_item(item.id, status=WorkItemStatus.IN_PROGRESS)
    assert updated.status == WorkItemStatus.IN_PROGRESS


def test_update_work_item_multiple_fields():
    """Test updating multiple fields at once."""
    board = create_sample_board()
    item = board.create_work_item(
        work_item_type=WorkItemType.TASK,
        title="Old Title",
        description="Old description",
        status=WorkItemStatus.TO_DO
    )
    
    updated = board.update_work_item(
        item.id,
        title="New Title",
        description="New description",
        status=WorkItemStatus.DONE
    )
    
    assert updated.title == "New Title"
    assert updated.description == "New description"
    assert updated.status == WorkItemStatus.DONE


def test_update_work_item_not_exists():
    """Test updating a work item that doesn't exist raises exception."""
    board = create_sample_board()
    non_existent_id = uuid.uuid4()
    
    with pytest.raises(WorkItemNotFoundError):
        board.update_work_item(non_existent_id, title="New Title")


# ==================== Work Item Deletion Tests ====================

def test_delete_work_item():
    """Test deleting a work item."""
    board = create_sample_board()
    item = board.create_work_item(
        work_item_type=WorkItemType.TASK,
        title="Test Task",
        description="Test"
    )
    
    assert item.id in board.work_items
    board.delete_work_item(item.id)
    assert item.id not in board.work_items


def test_delete_work_item_removes_from_parent():
    """Test that deleting a work item removes it from parent's children_ids."""
    board = create_sample_board()
    
    parent = board.create_work_item(
        work_item_type=WorkItemType.STORY,
        title="Parent",
        description="Parent"
    )
    
    child = board.create_work_item(
        work_item_type=WorkItemType.TASK,
        title="Child",
        description="Child",
        parent_id=parent.id
    )
    
    assert child.id in parent.children_ids
    board.delete_work_item(child.id)
    assert child.id not in parent.children_ids
    assert child.id not in board.work_items


def test_delete_work_item_removes_children_relationships():
    """Test that deleting a work item removes children's parent_id."""
    board = create_sample_board()
    
    parent = board.create_work_item(
        work_item_type=WorkItemType.STORY,
        title="Parent",
        description="Parent"
    )
    
    child1 = board.create_work_item(
        work_item_type=WorkItemType.TASK,
        title="Child 1",
        description="Child 1",
        parent_id=parent.id
    )
    
    child2 = board.create_work_item(
        work_item_type=WorkItemType.TASK,
        title="Child 2",
        description="Child 2",
        parent_id=parent.id
    )
    
    assert child1.parent_id == parent.id
    assert child2.parent_id == parent.id
    
    board.delete_work_item(parent.id)
    
    # Children should still exist but parent should be removed
    assert child1.id in board.work_items
    assert child2.id in board.work_items
    assert board.work_items[child1.id].parent_id is None
    assert board.work_items[child2.id].parent_id is None


def test_delete_work_item_not_exists():
    """Test deleting a work item that doesn't exist raises exception."""
    board = create_sample_board()
    non_existent_id = uuid.uuid4()
    
    with pytest.raises(WorkItemNotFoundError):
        board.delete_work_item(non_existent_id)


# ==================== Query Methods Tests ====================

def test_list_work_items_empty():
    """Test listing work items when board is empty."""
    board = create_sample_board()
    items = board.list_work_items()
    assert items == []
    assert len(items) == 0


def test_list_work_items_multiple():
    """Test listing multiple work items."""
    board = create_sample_board()
    
    item1 = board.create_work_item(
        work_item_type=WorkItemType.TASK,
        title="Task 1",
        description="Task 1"
    )
    item2 = board.create_work_item(
        work_item_type=WorkItemType.STORY,
        title="Story 1",
        description="Story 1"
    )
    item3 = board.create_work_item(
        work_item_type=WorkItemType.FEATURE,
        title="Feature 1",
        description="Feature 1"
    )
    
    items = board.list_work_items()
    assert len(items) == 3
    item_ids = {item.id for item in items}
    assert item_ids == {item1.id, item2.id, item3.id}


def test_list_by_type():
    """Test listing work items by type."""
    board = create_sample_board()
    
    task1 = board.create_work_item(
        work_item_type=WorkItemType.TASK,
        title="Task 1",
        description="Task 1"
    )
    task2 = board.create_work_item(
        work_item_type=WorkItemType.TASK,
        title="Task 2",
        description="Task 2"
    )
    story = board.create_work_item(
        work_item_type=WorkItemType.STORY,
        title="Story 1",
        description="Story 1"
    )
    
    tasks = board.list_by_type(WorkItemType.TASK)
    assert len(tasks) == 2
    task_ids = {task.id for task in tasks}
    assert task_ids == {task1.id, task2.id}
    assert story.id not in task_ids


def test_list_by_type_empty():
    """Test listing by type when no items of that type exist."""
    board = create_sample_board()
    
    board.create_work_item(
        work_item_type=WorkItemType.TASK,
        title="Task",
        description="Task"
    )
    
    features = board.list_by_type(WorkItemType.FEATURE)
    assert features == []


def test_list_by_status():
    """Test listing work items by status."""
    board = create_sample_board()
    
    todo1 = board.create_work_item(
        work_item_type=WorkItemType.TASK,
        title="Todo 1",
        description="Todo 1"
    )
    todo2 = board.create_work_item(
        work_item_type=WorkItemType.TASK,
        title="Todo 2",
        description="Todo 2"
    )
    
    # Update one to in_progress
    board.update_work_item(todo2.id, status=WorkItemStatus.IN_PROGRESS)
    
    todo_items = board.list_by_status(WorkItemStatus.TO_DO)
    assert len(todo_items) == 1
    assert todo_items[0].id == todo1.id
    
    in_progress_items = board.list_by_status(WorkItemStatus.IN_PROGRESS)
    assert len(in_progress_items) == 1
    assert in_progress_items[0].id == todo2.id


def test_list_by_status_empty():
    """Test listing by status when no items have that status."""
    board = create_sample_board()
    
    board.create_work_item(
        work_item_type=WorkItemType.TASK,
        title="Task",
        description="Task"
    )
    
    done_items = board.list_by_status(WorkItemStatus.DONE)
    assert done_items == []


# ==================== Relationship Methods Tests ====================

def test_add_child():
    """Test adding a child to a parent."""
    board = create_sample_board()
    
    parent = board.create_work_item(
        work_item_type=WorkItemType.STORY,
        title="Parent",
        description="Parent"
    )
    
    child = board.create_work_item(
        work_item_type=WorkItemType.TASK,
        title="Child",
        description="Child"
    )
    
    board.add_child(parent.id, child.id)
    
    assert child.id in parent.children_ids
    assert child.parent_id == parent.id


def test_add_child_parent_not_exists():
    """Test adding child when parent doesn't exist raises exception."""
    board = create_sample_board()
    
    child = board.create_work_item(
        work_item_type=WorkItemType.TASK,
        title="Child",
        description="Child"
    )
    
    non_existent_parent_id = uuid.uuid4()
    
    with pytest.raises(WorkItemNotFoundError):
        board.add_child(non_existent_parent_id, child.id)


def test_add_child_child_not_exists():
    """Test adding child when child doesn't exist raises exception."""
    board = create_sample_board()
    
    parent = board.create_work_item(
        work_item_type=WorkItemType.STORY,
        title="Parent",
        description="Parent"
    )
    
    non_existent_child_id = uuid.uuid4()
    
    with pytest.raises(WorkItemNotFoundError):
        board.add_child(parent.id, non_existent_child_id)


def test_add_child_max_children_limit():
    """Test that adding children respects the maximum children count limit."""
    board = create_sample_board()
    
    parent = board.create_work_item(
        work_item_type=WorkItemType.STORY,
        title="Parent",
        description="Parent"
    )
    
    # Add exactly MAX_CHILDREN_COUNT children - should work
    children = []
    for i in range(MAX_CHILDREN_COUNT):
        child = board.create_work_item(
            work_item_type=WorkItemType.TASK,
            title=f"Child {i}",
            description=f"Child {i} description"
        )
        board.add_child(parent.id, child.id)
        children.append(child)
    
    assert len(parent.children_ids) == MAX_CHILDREN_COUNT
    assert len(board.get_children(parent.id)) == MAX_CHILDREN_COUNT
    
    # Try to add one more child - should raise ValueError
    extra_child = board.create_work_item(
        work_item_type=WorkItemType.TASK,
        title="Extra Child",
        description="This should fail"
    )
    
    with pytest.raises(ValueError, match=f"must be less than {MAX_CHILDREN_COUNT}"):
        board.add_child(parent.id, extra_child.id)
    
    # Verify the extra child was not added
    assert len(parent.children_ids) == MAX_CHILDREN_COUNT
    assert extra_child.id not in parent.children_ids


def test_create_work_item_with_children_max_limit():
    """Test that creating a work item with children_ids respects the maximum limit."""
    board = create_sample_board()
    
    # Create exactly MAX_CHILDREN_COUNT children
    children = []
    for i in range(MAX_CHILDREN_COUNT):
        child = board.create_work_item(
            work_item_type=WorkItemType.TASK,
            title=f"Child {i}",
            description=f"Child {i} description"
        )
        children.append(child)
    
    # Create parent with all children - should work
    children_ids = [child.id for child in children]
    parent = board.create_work_item(
        work_item_type=WorkItemType.STORY,
        title="Parent",
        description="Parent",
        children_ids=children_ids
    )
    
    assert len(parent.children_ids) == MAX_CHILDREN_COUNT
    
    # Try to add one more child after creation - should fail
    extra_child = board.create_work_item(
        work_item_type=WorkItemType.TASK,
        title="Extra Child",
        description="This should fail"
    )
    
    with pytest.raises(ValueError, match=f"must be less than {MAX_CHILDREN_COUNT}"):
        board.add_child(parent.id, extra_child.id)


def test_create_work_item_with_too_many_children_fails():
    """Test that creating a work item with more than MAX_CHILDREN_COUNT children_ids fails validation."""
    board = create_sample_board()
    
    # Create MAX_CHILDREN_COUNT + 1 children
    children = []
    for i in range(MAX_CHILDREN_COUNT + 1):
        child = board.create_work_item(
            work_item_type=WorkItemType.TASK,
            title=f"Child {i}",
            description=f"Child {i} description"
        )
        children.append(child)
    
    # Try to create parent with too many children - should fail at WorkItem creation
    children_ids = [child.id for child in children]
    
    # This should fail because WorkItem has max_length=MAX_CHILDREN_COUNT on children_ids
    with pytest.raises(ValueError):
        board.create_work_item(
            work_item_type=WorkItemType.STORY,
            title="Parent",
            description="Parent",
            children_ids=children_ids
        )


def test_remove_child():
    """Test removing a child from a parent."""
    board = create_sample_board()
    
    parent = board.create_work_item(
        work_item_type=WorkItemType.STORY,
        title="Parent",
        description="Parent"
    )
    
    child = board.create_work_item(
        work_item_type=WorkItemType.TASK,
        title="Child",
        description="Child",
        parent_id=parent.id
    )
    
    assert child.id in parent.children_ids
    assert child.parent_id == parent.id
    
    board.remove_child(parent.id, child.id)
    
    assert child.id not in parent.children_ids
    assert child.parent_id is None


def test_remove_child_not_relationship():
    """Test removing child that is not actually a child raises exception."""
    board = create_sample_board()
    
    parent = board.create_work_item(
        work_item_type=WorkItemType.STORY,
        title="Parent",
        description="Parent"
    )
    
    child = board.create_work_item(
        work_item_type=WorkItemType.TASK,
        title="Child",
        description="Child"
    )
    
    # Child is not a child of parent
    with pytest.raises(WorkItemRelationshipError, match="is not a child"):
        board.remove_child(parent.id, child.id)


def test_get_children():
    """Test getting all children of a parent."""
    board = create_sample_board()
    
    parent = board.create_work_item(
        work_item_type=WorkItemType.STORY,
        title="Parent",
        description="Parent"
    )
    
    child1 = board.create_work_item(
        work_item_type=WorkItemType.TASK,
        title="Child 1",
        description="Child 1",
        parent_id=parent.id
    )
    
    child2 = board.create_work_item(
        work_item_type=WorkItemType.TASK,
        title="Child 2",
        description="Child 2",
        parent_id=parent.id
    )
    
    children = board.get_children(parent.id)
    assert len(children) == 2
    child_ids = {child.id for child in children}
    assert child_ids == {child1.id, child2.id}


def test_get_children_empty():
    """Test getting children when parent has no children."""
    board = create_sample_board()
    
    parent = board.create_work_item(
        work_item_type=WorkItemType.STORY,
        title="Parent",
        description="Parent"
    )
    
    children = board.get_children(parent.id)
    assert children == []


def test_get_children_parent_not_exists():
    """Test getting children when parent doesn't exist raises exception."""
    board = create_sample_board()
    non_existent_id = uuid.uuid4()
    
    with pytest.raises(WorkItemNotFoundError):
        board.get_children(non_existent_id)


def test_get_parent():
    """Test getting the parent of a child."""
    board = create_sample_board()
    
    parent = board.create_work_item(
        work_item_type=WorkItemType.STORY,
        title="Parent",
        description="Parent"
    )
    
    child = board.create_work_item(
        work_item_type=WorkItemType.TASK,
        title="Child",
        description="Child",
        parent_id=parent.id
    )
    
    found_parent = board.get_parent(child.id)
    assert found_parent is not None
    assert found_parent.id == parent.id


def test_get_parent_no_parent():
    """Test getting parent when child has no parent."""
    board = create_sample_board()
    
    child = board.create_work_item(
        work_item_type=WorkItemType.TASK,
        title="Child",
        description="Child"
    )
    
    found_parent = board.get_parent(child.id)
    assert found_parent is None


def test_get_parent_child_not_exists():
    """Test getting parent when child doesn't exist raises exception."""
    board = create_sample_board()
    non_existent_id = uuid.uuid4()
    
    with pytest.raises(WorkItemNotFoundError):
        board.get_parent(non_existent_id)


# ==================== Validation Tests ====================

def test_max_work_items_validation():
    """Test that board validates maximum work items count."""
    board = create_sample_board()
    
    # Create maximum number of items
    for i in range(MAX_WORK_ITEMS_COUNT):
        board.create_work_item(
            work_item_type=WorkItemType.TASK,
            title=f"Task {i}",
            description=f"Task {i} description"
        )
    
    # This should work
    assert len(board.work_items) == MAX_WORK_ITEMS_COUNT
    
    # Creating one more should fail validation
    with pytest.raises(ValueError, match="must be less than"):
        board.create_work_item(
            work_item_type=WorkItemType.TASK,
            title="One too many",
            description="This should fail"
        )


# ==================== Integration Tests ====================

def test_complete_workflow():
    """Test a complete workflow: create epic -> feature -> story -> task."""
    board = create_sample_board()
    
    # Create epic
    epic = board.create_work_item(
        work_item_type=WorkItemType.EPIC,
        title="User Authentication Epic",
        description="Epic for user authentication"
    )
    
    # Create feature under epic
    feature = board.create_work_item(
        work_item_type=WorkItemType.FEATURE,
        title="Login Feature",
        description="Feature for user login",
        parent_id=epic.id
    )
    
    # Create story under feature
    story = board.create_work_item(
        work_item_type=WorkItemType.STORY,
        title="Email Login Story",
        description="Story for email login",
        parent_id=feature.id
    )
    
    # Create task under story
    task = board.create_work_item(
        work_item_type=WorkItemType.TASK,
        title="Implement email validation",
        description="Task to implement email validation",
        parent_id=story.id
    )
    
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


def test_update_and_delete_workflow():
    """Test updating and deleting items in a workflow."""
    board = create_sample_board()
    
    # Create items
    parent = board.create_work_item(
        work_item_type=WorkItemType.STORY,
        title="Parent Story",
        description="Parent"
    )
    
    child1 = board.create_work_item(
        work_item_type=WorkItemType.TASK,
        title="Child 1",
        description="Child 1",
        parent_id=parent.id
    )
    
    child2 = board.create_work_item(
        work_item_type=WorkItemType.TASK,
        title="Child 2",
        description="Child 2",
        parent_id=parent.id
    )
    
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

