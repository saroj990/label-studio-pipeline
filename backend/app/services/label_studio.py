from __future__ import annotations

import xml.sax.saxutils as xml_escape

import httpx

from app.config import settings


class LabelStudioError(Exception):
    pass


class LabelStudioClient:
    def __init__(self) -> None:
        self.base = settings.label_studio_url.rstrip("/")
        self.token = settings.label_studio_api_token

    def _headers(self) -> dict[str, str]:
        if not self.token:
            raise LabelStudioError(
                "LABEL_STUDIO_API_TOKEN is not set in .env"
            )
        return {"Authorization": f"Token {self.token}"}

    def _client(self) -> httpx.Client:
        return httpx.Client(base_url=self.base, headers=self._headers(), timeout=60.0)

    @staticmethod
    def label_config(class_a: str, class_b: str) -> str:
        a = xml_escape.escape(class_a)
        b = xml_escape.escape(class_b)
        return f"""
<View>
  <Image name="image" value="$image"/>
  <Choices name="label" toName="image" choice="single">
    <Choice value="{a}"/>
    <Choice value="{b}"/>
  </Choices>
</View>
""".strip()

    def create_project(self, title: str, class_a: str, class_b: str) -> int:
        payload = {
            "title": title,
            "label_config": self.label_config(class_a, class_b),
        }
        with self._client() as client:
            response = client.post("/api/projects/", json=payload)
            if response.status_code >= 400:
                raise LabelStudioError(
                    f"Create project failed: {response.status_code} {response.text}"
                )
            return int(response.json()["id"])

    def import_tasks(self, project_id: int, tasks: list[dict]) -> None:
        with self._client() as client:
            response = client.post(
                f"/api/projects/{project_id}/import",
                json=tasks,
            )
            if response.status_code >= 400:
                raise LabelStudioError(
                    f"Import tasks failed: {response.status_code} {response.text}"
                )

    def list_tasks(self, project_id: int) -> list[dict]:
        tasks: list[dict] = []
        page = 1
        with self._client() as client:
            while True:
                response = client.get(
                    "/api/tasks/",
                    params={"project": project_id, "page": page, "page_size": 100},
                )
                if response.status_code >= 400:
                    raise LabelStudioError(
                        f"List tasks failed: {response.status_code} {response.text}"
                    )
                batch = response.json()
                if not batch:
                    break
                tasks.extend(batch)
                if len(batch) < 100:
                    break
                page += 1
        return tasks

    def export_json(self, project_id: int) -> list[dict]:
        with self._client() as client:
            response = client.get(
                f"/api/projects/{project_id}/export",
                params={"exportType": "JSON"},
            )
            if response.status_code >= 400:
                raise LabelStudioError(
                    f"Export failed: {response.status_code} {response.text}"
                )
            data = response.json()
            if isinstance(data, list):
                return data
            return []

    def create_annotation(self, task_id: int, choice: str) -> None:
        payload = {
            "result": [
                {
                    "from_name": "label",
                    "to_name": "image",
                    "type": "choices",
                    "value": {"choices": [choice]},
                }
            ]
        }
        with self._client() as client:
            response = client.post(
                f"/api/tasks/{task_id}/annotations/",
                json=payload,
            )
            if response.status_code >= 400:
                raise LabelStudioError(
                    f"Create annotation failed: {response.status_code} {response.text}"
                )

    def project_url(self, project_id: int) -> str:
        return f"{self.base}/projects/{project_id}/data"
