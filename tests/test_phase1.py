from io import BytesIO

from fastapi.testclient import TestClient
from PIL import Image

from src.api_app import create_app
from src.iteracanvas_config import Settings


def client(tmp_path):
    return TestClient(create_app(Settings(runtime_dir=tmp_path / "runtime")))


def png(color: str) -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (32, 32), color).save(buffer, format="PNG")
    return buffer.getvalue()


def create_active_task(test_client):
    task = test_client.post("/api/v1/tasks", json={"title": "商品海报"}).json()
    spec = test_client.post(
        f"/api/v1/tasks/{task['id']}/spec-versions",
        json={"spec": {"context": {"purpose": "电商主图"}, "criteria": [{"category": "subject", "statement": "主体清晰", "importance": "hard"}]}},
    ).json()
    confirmed = test_client.post(f"/api/v1/spec-versions/{spec['id']}/confirm").json()
    return task, confirmed


def test_phase1_round_upload_duplicate_and_cross_round(tmp_path):
    with client(tmp_path) as test_client:
        task, spec = create_active_task(test_client)
        round_one = test_client.post(
            f"/api/v1/tasks/{task['id']}/rounds",
            json={"spec_version_id": spec["id"], "prompt_snapshot": "商品摄影", "params": {"size": "1:1"}},
        ).json()

        files = [
            ("files", ("one.png", png("red"), "image/png")),
            ("files", ("two.png", png("blue"), "image/png")),
        ]
        submission = test_client.post(f"/api/v1/rounds/{round_one['id']}/submissions", files=files)
        assert submission.status_code == 201
        assert len(submission.json()["candidates"]) == 2

        duplicate = test_client.post(
            f"/api/v1/rounds/{round_one['id']}/submissions",
            files=[("files", ("again.png", png("red"), "image/png"))],
        )
        assert duplicate.status_code == 409
        assert duplicate.json()["code"] == "DUPLICATE_CANDIDATE"

        round_two = test_client.post(
            f"/api/v1/tasks/{task['id']}/rounds",
            json={"spec_version_id": spec["id"]},
        ).json()
        cross_round = test_client.post(
            f"/api/v1/rounds/{round_two['id']}/submissions",
            files=[("files", ("same.png", png("red"), "image/png"))],
        )
        assert cross_round.status_code == 201
        assert cross_round.json()["candidates"][0]["cross_round_duplicate"] is True

        detail = test_client.get(f"/api/v1/tasks/{task['id']}").json()
        assert len(detail["rounds"]) == 2
        assert detail["status"] == "active"


def test_idempotency_and_leaf_delete(tmp_path):
    with client(tmp_path) as test_client:
        headers = {"Idempotency-Key": "task-1"}
        first = test_client.post("/api/v1/tasks", headers=headers, json={"title": "幂等任务"})
        second = test_client.post("/api/v1/tasks", headers=headers, json={"title": "幂等任务"})
        assert first.status_code == second.status_code == 201
        assert first.json()["id"] == second.json()["id"]

        task, _ = create_active_task(test_client)
        branch = test_client.post(f"/api/v1/tasks/{task['id']}/branches", json={}).json()
        blocked = test_client.delete(f"/api/v1/tasks/{task['id']}")
        assert blocked.status_code == 409
        assert branch["id"] in blocked.json()["details"]["blocking_task_ids"]
        assert test_client.delete(f"/api/v1/tasks/{branch['id']}").status_code == 200
        assert test_client.delete(f"/api/v1/tasks/{task['id']}").status_code == 200

