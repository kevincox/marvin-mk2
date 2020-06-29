from typing import Any
from typing import Dict
from typing import List
from typing import Tuple

from gidgethub import sansio

from marvin import __main__ as main


class GitHubAPIMock:
    def __init__(self) -> None:
        self.post_data: List[Tuple[str, Dict[str, Any]]] = []
        self.delete_urls: List[str] = []

    async def post(self, url: str, oauth_token: str, data: Dict[str, Any]) -> None:
        self.post_data.append((url, data))

    async def delete(self, url: str, oauth_token: str) -> None:
        self.delete_urls.append(url)


async def test_adds_awaiting_reviewer_label() -> None:
    data = {
        "action": "created",
        "issue": {
            "url": "issue-url",
            "pull_request": {"url": "pr-url"},
            "user": {"id": 42, "login": "somebody"},
            "labels": [{"name": "marvin"}],
        },
        "comment": {
            "body": "/status awaiting_reviewer",
            "user": {"id": 42, "login": "somebody"},
        },
    }
    event = sansio.Event(data, event="issue_comment", delivery_id="1")
    gh = GitHubAPIMock()
    await main.router.dispatch(event, gh, token="fake-token")
    assert gh.post_data == [("issue-url/labels", {"labels": ["awaiting_reviewer"]})]


async def test_removes_old_status_labels_on_new_status() -> None:
    data = {
        "action": "created",
        "issue": {
            "url": "issue-url",
            "pull_request": {"url": "pr-url"},
            "user": {"id": 42, "login": "somebody"},
            "labels": [
                {"name": "marvin"},
                {"name": "awaiting_changes"},
                {"name": "needs_merger"},
            ],
        },
        "comment": {
            "body": "/status awaiting_reviewer",
            "user": {"id": 42, "login": "somebody"},
        },
    }
    event = sansio.Event(data, event="issue_comment", delivery_id="1")
    gh = GitHubAPIMock()
    await main.router.dispatch(event, gh, token="fake-token")
    assert gh.post_data == [("issue-url/labels", {"labels": ["awaiting_reviewer"]})]
    assert set(gh.delete_urls) == {
        "issue-url/labels/needs_merger",
        "issue-url/labels/awaiting_changes",
    }


async def test_sets_to_awaiting_changes_on_non_author_comment() -> None:
    data = {
        "action": "created",
        "issue": {
            "url": "issue-url",
            "pull_request": {"url": "pr-url"},
            "user": {"id": 42, "login": "somebody"},
            "labels": [{"name": "marvin"}, {"name": "needs_merger"}],
        },
        "comment": {
            "body": "The body is irrelevant.",
            "user": {"id": 43, "login": "somebody_else"},
        },
    }
    event = sansio.Event(data, event="issue_comment", delivery_id="1")
    gh = GitHubAPIMock()
    await main.router.dispatch(event, gh, token="fake-token")
    assert gh.post_data == [("issue-url/labels", {"labels": ["awaiting_changes"]})]
    assert set(gh.delete_urls) == {
        "issue-url/labels/needs_merger",
    }
