from io import BytesIO
import json
from pathlib import Path

from fastapi.testclient import TestClient
from PIL import Image

from src.api_app import create_app
from src.ai_gateway import DiagnosisResult, PatchResult, SpecExtractionResult
from src.iteracanvas_config import Settings


def png(color: str) -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (32, 32), color).save(buffer, format="PNG")
    return buffer.getvalue()


def test_mock_fixtures_match_ai_contracts():
    fixture_dir = Path(__file__).parent / "fixtures"
    SpecExtractionResult.model_validate(json.loads((fixture_dir / "ai_spec_result.json").read_text(encoding="utf-8")))
    DiagnosisResult.model_validate(json.loads((fixture_dir / "ai_diagnosis_result.json").read_text(encoding="utf-8")))
    PatchResult.model_validate(json.loads((fixture_dir / "ai_patch_result.json").read_text(encoding="utf-8")))


def test_phase2_mock_diagnosis_review_patch_compare_accept(tmp_path):
    with TestClient(create_app(Settings(runtime_dir=tmp_path / "runtime"))) as client:
        task = client.post("/api/v1/tasks", json={"title": "Mock 闭环", "description": "电商海报"}).json()
        extraction = client.post(f"/api/v1/tasks/{task['id']}/spec-extractions", json={}).json()
        assert extraction["context"]["description"] == "电商海报"
        spec = client.post(
            f"/api/v1/tasks/{task['id']}/spec-versions",
            json={
                "spec": {
                    "context": {"purpose": "电商主图"},
                    "criteria": [{"category": "text", "statement": "标签清晰", "importance": "hard"}],
                }
            },
        ).json()
        confirmed = client.post(f"/api/v1/spec-versions/{spec['id']}/confirm").json()
        round_one = client.post(
            f"/api/v1/tasks/{task['id']}/rounds",
            json={"spec_version_id": confirmed["id"], "prompt_snapshot": "黑金商品海报", "params": {"size": "1:1"}},
        ).json()
        candidate_one = client.post(
            f"/api/v1/rounds/{round_one['id']}/submissions",
            files=[("files", ("one.png", png("red"), "image/png"))],
        ).json()["candidates"][0]

        started = client.post(f"/api/v1/candidates/{candidate_one['id']}/diagnoses")
        assert started.status_code == 202
        diagnosis_one = client.get(f"/api/v1/diagnoses/{started.json()['id']}").json()
        assert diagnosis_one["status"] == "succeeded"
        item = diagnosis_one["effective_items"][0]
        assert item["verdict"] == "fail"

        review = client.post(
            f"/api/v1/diagnoses/{diagnosis_one['id']}/reviews",
            json={
                "item_id": item["item_id"],
                "decision": "correct",
                "corrected": {"evidence": {"description": "用户确认标签仍不清晰", "region": "中央"}},
            },
        )
        assert review.status_code == 201
        reviewed = client.get(f"/api/v1/diagnoses/{diagnosis_one['id']}").json()
        assert reviewed["result"]["items"][0]["evidence"]["description"] != "用户确认标签仍不清晰"
        assert reviewed["effective_items"][0]["evidence"]["description"] == "用户确认标签仍不清晰"
        assert reviewed["effective_items"][0]["resolution"] == "corrected"
        patch = client.post(
            f"/api/v1/rounds/{round_one['id']}/patches",
            json={"selected_item_ids": [item["item_id"]]},
        )
        assert patch.status_code == 201
        assert patch.json()["result"]["merged_prompt"]

        round_two = client.post(
            f"/api/v1/tasks/{task['id']}/rounds",
            json={"spec_version_id": confirmed["id"], "prompt_snapshot": patch.json()["result"]["merged_prompt"], "params": {"size": "1:1"}},
        ).json()
        candidate_two = client.post(
            f"/api/v1/rounds/{round_two['id']}/submissions",
            files=[("files", ("two.png", png("blue"), "image/png"))],
        ).json()["candidates"][0]
        diagnosis_two = client.post(f"/api/v1/candidates/{candidate_two['id']}/diagnoses").json()
        assert client.get(f"/api/v1/diagnoses/{diagnosis_two['id']}").json()["status"] == "succeeded"

        comparison = client.get(f"/api/v1/rounds/{round_two['id']}/comparison").json()
        assert comparison["items"][0]["outcome"] == "improved"
        accepted = client.post(f"/api/v1/tasks/{task['id']}/accept", json={"candidate_id": candidate_two["id"]})
        assert accepted.status_code == 200
        assert accepted.json()["status"] == "accepted"
