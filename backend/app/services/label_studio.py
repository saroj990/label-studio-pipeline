from __future__ import annotations

import xml.sax.saxutils as xml_escape

import httpx

from app.config import settings


class LabelStudioError(Exception):
    pass


def _looks_like_jwt(token: str) -> bool:
    return token.count(".") == 2 and token.startswith("eyJ")


class LabelStudioClient:
    """Talks to Label Studio HTTP API.

    LABEL_STUDIO_API_TOKEN may be:
    - Legacy API token → Authorization: Token <value>
    - Personal access token (JWT refresh) → exchange via /api/token/refresh, then Bearer
    """

    def __init__(self) -> None:
        self.base = settings.label_studio_url.rstrip("/")
        self.token = (settings.label_studio_api_token or "").strip()
        self._cached_bearer: str | None = None

    def _headers(self) -> dict[str, str]:
        if not self.token:
            raise LabelStudioError(
                "LABEL_STUDIO_API_TOKEN is not set in .env"
            )
        if _looks_like_jwt(self.token):
            if not self._cached_bearer:
                self._cached_bearer = self._refresh_access_token(self.token)
            return {"Authorization": f"Bearer {self._cached_bearer}"}
        return {"Authorization": f"Token {self.token}"}

    def _refresh_access_token(self, refresh_token: str) -> str:
        with httpx.Client(base_url=self.base, timeout=60.0) as client:
            response = client.post(
                "/api/token/refresh",
                json={"refresh": refresh_token},
            )
            if response.status_code >= 400:
                raise LabelStudioError(
                    "Personal access token refresh failed "
                    f"({response.status_code}): {response.text}. "
                    "Use Account & Settings → Legacy Token for simpler "
                    "Authorization: Token auth, or paste a valid PAT refresh token."
                )
            access = response.json().get("access")
            if not access:
                raise LabelStudioError(
                    "Token refresh did not return an access token. "
                    "Try a Legacy Token from Label Studio instead."
                )
            return str(access)

    def _invalidate_bearer_cache(self) -> None:
        self._cached_bearer = None

    def _client(self) -> httpx.Client:
        return httpx.Client(base_url=self.base, headers=self._headers(), timeout=60.0)

    def _request(self, method: str, url: str, **kwargs) -> httpx.Response:
        with self._client() as client:
            response = client.request(method, url, **kwargs)
            if (
                response.status_code == 401
                and _looks_like_jwt(self.token)
            ):
                self._invalidate_bearer_cache()
                with self._client() as retry_client:
                    response = retry_client.request(method, url, **kwargs)
            return response

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
        response = self._request("POST", "/api/projects/", json=payload)
        if response.status_code >= 400:
            raise LabelStudioError(
                f"Create project failed: {response.status_code} {response.text}"
            )
        return int(response.json()["id"])

    def import_tasks(self, project_id: int, tasks: list[dict]) -> None:
        response = self._request(
            "POST",
            f"/api/projects/{project_id}/import",
            json=tasks,
        )
        if response.status_code >= 400:
            raise LabelStudioError(
                f"Import tasks failed: {response.status_code} {response.text}"
            )

    @staticmethod
    def _tasks_from_page_payload(payload: object) -> list[dict]:
        if isinstance(payload, list):
            return [t for t in payload if isinstance(t, dict)]
        if isinstance(payload, dict):
            nested = payload.get("tasks")
            if isinstance(nested, list):
                return [t for t in nested if isinstance(t, dict)]
        return []

    def list_tasks(self, project_id: int) -> list[dict]:
        tasks: list[dict] = []
        page = 1
        page_size = 100
        while True:
            response = self._request(
                "GET",
                "/api/tasks/",
                params={"project": project_id, "page": page, "page_size": page_size},
            )
            if response.status_code >= 400:
                raise LabelStudioError(
                    f"List tasks failed: {response.status_code} {response.text}"
                )
            batch = self._tasks_from_page_payload(response.json())
            if not batch:
                break
            tasks.extend(batch)
            if len(batch) < page_size:
                break
            page += 1
        return tasks

    def export_json(self, project_id: int) -> list[dict]:
        response = self._request(
            "GET",
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
        response = self._request(
            "POST",
            f"/api/tasks/{task_id}/annotations/",
            json=payload,
        )
        if response.status_code >= 400:
            raise LabelStudioError(
                f"Create annotation failed: {response.status_code} {response.text}"
            )

    def project_url(self, project_id: int) -> str:
        return f"{self.base}/projects/{project_id}/data"
