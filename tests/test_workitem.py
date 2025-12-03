import uuid
from datetime import datetime, timedelta
import pytest
from pydantic import ValidationError

from src.models.workitem import WorkItem, WorkItemStatus, WorkItemType


def create_sample_work_item(**overrides) -> WorkItem:
    data = {
        "work_item_type": WorkItemType.TASK,
        "title": "Test title",
        "description": "Test description",
    }
    data.update(overrides)
    return WorkItem(**data)


def test_work_item_creation_defaults():
    item = create_sample_work_item()

    assert isinstance(item.id, uuid.UUID)
    assert item.status == WorkItemStatus.TO_DO
    assert item.work_item_type == WorkItemType.TASK
    assert item.title == "Test title"
    assert item.description == "Test description"

    # created_at should be close to "now"
    now = datetime.now()
    assert now - timedelta(seconds=5) <= item.created_at <= now + timedelta(seconds=5)


def test_work_item_status_transitions():
    item = create_sample_work_item()

    item.start()
    assert item.status == WorkItemStatus.IN_PROGRESS

    item.complete()
    assert item.status == WorkItemStatus.DONE

    item.reset()
    assert item.status == WorkItemStatus.TO_DO


def test_work_item_title_and_description_validation():
    with pytest.raises(ValidationError):
        create_sample_work_item(title="")

    with pytest.raises(ValidationError):
        create_sample_work_item(description="")


def test_frozen_fields_cannot_be_modified():
    item = create_sample_work_item()

    with pytest.raises(ValidationError):
        item.id = uuid.uuid4()

    with pytest.raises(ValidationError):
        item.work_item_type = WorkItemType.EPIC

    with pytest.raises(ValidationError):
        item.created_at = datetime.now()


def test_str_representation():
    item = create_sample_work_item(
        work_item_type=WorkItemType.FEATURE,
        title="Implement tests",
    )

    assert str(item) == "feature Implement tests"


def test_repr_contains_key_fields():
    item = create_sample_work_item(
        work_item_type=WorkItemType.STORY,
        title="User can create tasks",
    )

    rep = repr(item)
    assert str(item.id) in rep
    assert "story" in rep
    assert "User can create tasks" in rep
