import uuid
from datetime import datetime, timedelta

import pytest
from pydantic import ValidationError

from src.models.workitem import WorkItem, WorkItemStatus, WorkItemType, MAX_CHILDREN_COUNT


def create_sample_work_item(**overrides) -> WorkItem:
    data = {
        "work_item_type": WorkItemType.TASK,
        "title": "Test title",
        "description": "Test description",
    }
    data.update(overrides)
    return WorkItem(**data)


class TestWorkItemBasics:
    def test_creation_defaults(self):
        item = create_sample_work_item()

        assert isinstance(item.id, uuid.UUID)
        assert item.status == WorkItemStatus.TO_DO
        assert item.work_item_type == WorkItemType.TASK
        assert item.title == "Test title"
        assert item.description == "Test description"

        # created_at should be close to "now"
        now = datetime.now()
        assert now - timedelta(seconds=5) <= item.created_at <= now + timedelta(seconds=5)

    def test_status_transitions(self):
        item = create_sample_work_item()

        item.start()
        assert item.status == WorkItemStatus.IN_PROGRESS

        item.complete()
        assert item.status == WorkItemStatus.DONE

        item.reset()
        assert item.status == WorkItemStatus.TO_DO

    def test_title_and_description_validation(self):
        with pytest.raises(ValidationError):
            create_sample_work_item(title="")

        with pytest.raises(ValidationError):
            create_sample_work_item(description="")

    def test_frozen_fields_cannot_be_modified(self):
        item = create_sample_work_item()

        with pytest.raises(ValidationError):
            item.id = uuid.uuid4()

        with pytest.raises(ValidationError):
            item.work_item_type = WorkItemType.EPIC

        with pytest.raises(ValidationError):
            item.created_at = datetime.now()

    def test_str_representation(self):
        item = create_sample_work_item(
            work_item_type=WorkItemType.FEATURE,
            title="Implement tests",
        )

        assert str(item) == "feature Implement tests"

    def test_repr_contains_key_fields(self):
        item = create_sample_work_item(
            work_item_type=WorkItemType.STORY,
            title="User can create tasks",
        )

        rep = repr(item)
        assert str(item.id) in rep
        assert "story" in rep
        assert "User can create tasks" in rep


class TestWorkItemParentAndChildrenFields:
    def test_parent_id_defaults_to_none(self):
        """Test that parent_id defaults to None when not specified."""
        item = create_sample_work_item()
        assert item.parent_id is None

    def test_children_ids_defaults_to_empty_list(self):
        """Test that children_ids defaults to an empty list when not specified."""
        item = create_sample_work_item()
        assert item.children_ids == []
        assert isinstance(item.children_ids, list)
        assert len(item.children_ids) == 0

    def test_with_parent_id(self):
        """Test creating a WorkItem with a parent_id."""
        parent_id = uuid.uuid4()
        item = create_sample_work_item(parent_id=parent_id)

        assert item.parent_id == parent_id
        assert isinstance(item.parent_id, uuid.UUID)

    def test_with_children_ids(self):
        """Test creating a WorkItem with children_ids."""
        child_id_1 = uuid.uuid4()
        child_id_2 = uuid.uuid4()
        child_id_3 = uuid.uuid4()
        children_ids = [child_id_1, child_id_2, child_id_3]

        item = create_sample_work_item(children_ids=children_ids)

        assert item.children_ids == children_ids
        assert len(item.children_ids) == 3
        assert child_id_1 in item.children_ids
        assert child_id_2 in item.children_ids
        assert child_id_3 in item.children_ids

    def test_with_parent_and_children(self):
        """Test creating a WorkItem with both parent_id and children_ids."""
        parent_id = uuid.uuid4()
        child_id_1 = uuid.uuid4()
        child_id_2 = uuid.uuid4()
        children_ids = [child_id_1, child_id_2]

        item = create_sample_work_item(
            parent_id=parent_id,
            children_ids=children_ids,
        )

        assert item.parent_id == parent_id
        assert item.children_ids == children_ids
        assert len(item.children_ids) == 2

    def test_parent_id_can_be_set_to_none_explicitly(self):
        """Test that parent_id can be explicitly set to None."""
        item = create_sample_work_item(parent_id=None)
        assert item.parent_id is None

    def test_children_ids_can_be_empty_list(self):
        """Test that children_ids can be explicitly set to an empty list."""
        item = create_sample_work_item(children_ids=[])
        assert item.children_ids == []
        assert len(item.children_ids) == 0

    def test_parent_id_validation_requires_valid_uuid(self):
        """Test that parent_id must be a valid UUID or None."""
        # Valid UUID should work
        parent_id = uuid.uuid4()
        item = create_sample_work_item(parent_id=parent_id)
        assert item.parent_id == parent_id

        # None should work
        item = create_sample_work_item(parent_id=None)
        assert item.parent_id is None

        # Invalid UUID should raise ValidationError
        with pytest.raises(ValidationError):
            create_sample_work_item(parent_id="not-a-uuid")

    def test_children_ids_validation_requires_valid_uuids(self):
        """Test that children_ids must contain valid UUIDs."""
        valid_uuid_1 = uuid.uuid4()
        valid_uuid_2 = uuid.uuid4()

        # Valid UUIDs should work
        item = create_sample_work_item(children_ids=[valid_uuid_1, valid_uuid_2])
        assert len(item.children_ids) == 2

        # Invalid UUID in list should raise ValidationError
        with pytest.raises(ValidationError):
            create_sample_work_item(children_ids=[valid_uuid_1, "not-a-uuid"])

        # Non-list should raise ValidationError
        with pytest.raises(ValidationError):
            create_sample_work_item(children_ids="not-a-list")

    def test_children_ids_can_be_modified(self):
        """Test that children_ids list can be modified (unlike frozen fields)."""
        item = create_sample_work_item()
        assert item.children_ids == []

        # Should be able to append to children_ids
        child_id = uuid.uuid4()
        item.children_ids.append(child_id)
        assert len(item.children_ids) == 1
        assert child_id in item.children_ids

        # Should be able to extend children_ids
        child_id_2 = uuid.uuid4()
        child_id_3 = uuid.uuid4()
        item.children_ids.extend([child_id_2, child_id_3])
        assert len(item.children_ids) == 3

    def test_parent_id_can_be_modified(self):
        """Test that parent_id can be modified (unlike frozen fields)."""
        item = create_sample_work_item()
        assert item.parent_id is None

        # Should be able to set parent_id
        parent_id = uuid.uuid4()
        item.parent_id = parent_id
        assert item.parent_id == parent_id

        # Should be able to change parent_id
        new_parent_id = uuid.uuid4()
        item.parent_id = new_parent_id
        assert item.parent_id == new_parent_id

        # Should be able to set to None
        item.parent_id = None
        assert item.parent_id is None

    def test_parent_child_relationship_example(self):
        """Test a realistic parent-child relationship scenario."""
        # Create a parent epic
        epic = create_sample_work_item(
            work_item_type=WorkItemType.EPIC,
            title="User Authentication Epic",
        )

        # Create a feature that belongs to the epic
        feature = create_sample_work_item(
            work_item_type=WorkItemType.FEATURE,
            title="Login Feature",
            parent_id=epic.id,
        )

        # Create stories that belong to the feature
        story_1 = create_sample_work_item(
            work_item_type=WorkItemType.STORY,
            title="User can login with email",
            parent_id=feature.id,
        )
        story_2 = create_sample_work_item(
            work_item_type=WorkItemType.STORY,
            title="User can login with Google",
            parent_id=feature.id,
        )

        # Add stories to feature's children_ids
        feature.children_ids = [story_1.id, story_2.id]

        # Verify relationships
        assert feature.parent_id == epic.id
        assert story_1.parent_id == feature.id
        assert story_2.parent_id == feature.id
        assert feature.children_ids == [story_1.id, story_2.id]
        assert len(feature.children_ids) == 2

    def test_children_ids_preserves_order(self):
        """Test that children_ids preserves the order of UUIDs."""
        child_id_1 = uuid.uuid4()
        child_id_2 = uuid.uuid4()
        child_id_3 = uuid.uuid4()
        children_ids = [child_id_1, child_id_2, child_id_3]

        item = create_sample_work_item(children_ids=children_ids)

        assert item.children_ids[0] == child_id_1
        assert item.children_ids[1] == child_id_2
        assert item.children_ids[2] == child_id_3

    def test_multiple_items_with_same_parent(self):
        """Test multiple WorkItems can share the same parent_id."""
        parent_id = uuid.uuid4()

        item_1 = create_sample_work_item(
            title="Item 1",
            parent_id=parent_id,
        )
        item_2 = create_sample_work_item(
            title="Item 2",
            parent_id=parent_id,
        )
        item_3 = create_sample_work_item(
            title="Item 3",
            parent_id=parent_id,
        )

        assert item_1.parent_id == parent_id
        assert item_2.parent_id == parent_id
        assert item_3.parent_id == parent_id
        assert item_1.parent_id == item_2.parent_id == item_3.parent_id

    def test_work_item_can_have_multiple_children(self):
        """Test that a WorkItem can have multiple children."""
        parent = create_sample_work_item(
            work_item_type=WorkItemType.FEATURE,
            title="Parent Feature",
        )

        child_1 = create_sample_work_item(
            work_item_type=WorkItemType.STORY,
            title="Child 1",
        )
        child_2 = create_sample_work_item(
            work_item_type=WorkItemType.STORY,
            title="Child 2",
        )
        child_3 = create_sample_work_item(
            work_item_type=WorkItemType.STORY,
            title="Child 3",
        )

        parent.children_ids = [child_1.id, child_2.id, child_3.id]

        assert len(parent.children_ids) == 3
        assert child_1.id in parent.children_ids
        assert child_2.id in parent.children_ids
        assert child_3.id in parent.children_ids

    def test_children_ids_can_be_cleared(self):
        """Test that children_ids can be cleared."""
        child_id_1 = uuid.uuid4()
        child_id_2 = uuid.uuid4()

        item = create_sample_work_item(children_ids=[child_id_1, child_id_2])
        assert len(item.children_ids) == 2

        item.children_ids.clear()
        assert len(item.children_ids) == 0
        assert item.children_ids == []


class TestWorkItemChildrenConstraints:
    def test_children_ids_uniqueness_enforced_on_creation(self):
        """Test that uniqueness is enforced when creating WorkItem with duplicate children_ids."""
        child_id_1 = uuid.uuid4()
        child_id_2 = uuid.uuid4()

        # Valid: Creating with unique IDs
        item = create_sample_work_item(children_ids=[child_id_1, child_id_2])
        assert len(item.children_ids) == 2

        # Invalid: Creating with duplicate IDs should raise ValueError
        duplicate_id = uuid.uuid4()
        with pytest.raises(ValueError, match="children_ids must contain unique UUIDs"):
            create_sample_work_item(children_ids=[duplicate_id, duplicate_id])

        # Invalid: Creating with mixed unique and duplicate IDs
        with pytest.raises(ValueError, match="children_ids must contain unique UUIDs"):
            create_sample_work_item(children_ids=[child_id_1, child_id_2, child_id_1])

    def test_children_ids_uniqueness_enforced_on_validation(self):
        """Test that uniqueness is enforced when validating a WorkItem."""
        child_id_1 = uuid.uuid4()
        child_id_2 = uuid.uuid4()

        # Create a valid item
        item = create_sample_work_item(children_ids=[child_id_1, child_id_2])

        # Modify children_ids in place (this won't trigger validation automatically)
        item.children_ids.append(child_id_1)  # Adding duplicate

        # But validation should catch it when we re-validate
        with pytest.raises(ValueError, match="children_ids must contain unique UUIDs"):
            WorkItem.model_validate(item.model_dump())

    def test_children_ids_max_length_limit(self):
        """Test that children_ids cannot exceed MAX_CHILDREN_COUNT."""
        # Valid: Creating with exactly MAX_CHILDREN_COUNT children
        max_children = [uuid.uuid4() for _ in range(MAX_CHILDREN_COUNT)]
        item = create_sample_work_item(children_ids=max_children)
        assert len(item.children_ids) == MAX_CHILDREN_COUNT

        # Valid: Creating with fewer than MAX_CHILDREN_COUNT children
        fewer_children = [uuid.uuid4() for _ in range(MAX_CHILDREN_COUNT - 1)]
        item = create_sample_work_item(children_ids=fewer_children)
        assert len(item.children_ids) == MAX_CHILDREN_COUNT - 1

        # Invalid: Creating with more than MAX_CHILDREN_COUNT children should raise ValidationError
        too_many_children = [uuid.uuid4() for _ in range(MAX_CHILDREN_COUNT + 1)]
        with pytest.raises(ValidationError):
            create_sample_work_item(children_ids=too_many_children)

        # Invalid: Creating with significantly more than MAX_CHILDREN_COUNT
        way_too_many = [uuid.uuid4() for _ in range(MAX_CHILDREN_COUNT + 50)]
        with pytest.raises(ValidationError):
            create_sample_work_item(children_ids=way_too_many)


class TestWorkItemHelperMethods:
    def test_add_parent_sets_parent_id(self):
        """add_parent should set parent_id to the given UUID."""
        item = create_sample_work_item()
        assert item.parent_id is None

        parent_id = uuid.uuid4()
        item.add_parent(parent_id)

        assert item.parent_id == parent_id

    def test_remove_parent_clears_parent_id(self):
        """remove_parent should set parent_id to None."""
        parent_id = uuid.uuid4()
        item = create_sample_work_item(parent_id=parent_id)
        assert item.parent_id == parent_id

        item.remove_parent()

        assert item.parent_id is None

    def test_add_child_appends_child_id(self):
        """add_child should append a new child_id to children_ids."""
        item = create_sample_work_item()
        assert item.children_ids == []

        child_id = uuid.uuid4()
        item.add_child(child_id)

        assert len(item.children_ids) == 1
        assert item.children_ids[0] == child_id

    def test_add_child_is_idempotent_if_child_already_present(self):
        """add_child should do nothing (be idempotent) if the child is already in children_ids."""
        item = create_sample_work_item()
        child_id = uuid.uuid4()

        item.add_child(child_id)
        assert child_id in item.children_ids

        # Second call should not raise and should not duplicate the child_id
        item.add_child(child_id)
        assert item.children_ids.count(child_id) == 1

    def test_add_child_respects_max_children_count(self):
        """add_child should not allow adding more than MAX_CHILDREN_COUNT children."""
        item = create_sample_work_item()

        # Pre-fill to the max
        for _ in range(MAX_CHILDREN_COUNT):
            item.children_ids.append(uuid.uuid4())

        assert len(item.children_ids) == MAX_CHILDREN_COUNT

        # Now adding via helper should fail
        with pytest.raises(ValueError, match="must not exceed"):
            item.add_child(uuid.uuid4())

    def test_remove_child_removes_existing_child(self):
        """remove_child should remove the given child_id from children_ids."""
        child_id_1 = uuid.uuid4()
        child_id_2 = uuid.uuid4()
        item = create_sample_work_item(children_ids=[child_id_1, child_id_2])

        item.remove_child(child_id_1)

        assert child_id_1 not in item.children_ids
        assert child_id_2 in item.children_ids

    def test_remove_child_raises_if_child_not_present(self):
        """remove_child should raise if the given child_id is not in children_ids."""
        child_id = uuid.uuid4()
        item = create_sample_work_item()
        assert child_id not in item.children_ids

        with pytest.raises(ValueError, match="not a child"):
            item.remove_child(child_id)


