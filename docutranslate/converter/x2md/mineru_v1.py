"""MinerU 4.x V1 transport, shared by synchronous and asynchronous callers."""

import asyncio
import hashlib
import mimetypes
import time
from urllib.parse import quote, urljoin, urlsplit


TIERS = {"flash", "basic", "standard", "advanced"}
NATIVE_SUFFIXES = {
    ".doc", ".docx", ".ppt", ".pptx", ".xls", ".xlsx", ".rtf",
    ".odt", ".ods", ".odp", ".epub", ".ofd", ".html", ".htm", ".csv", ".tsv",
}


def _origin(url):
    parts = urlsplit(url)
    if parts.scheme not in {"http", "https"} or not parts.hostname:
        raise RuntimeError("MinerU V1 returned an invalid HTTP URL")
    return parts.scheme, parts.hostname, parts.port or (443 if parts.scheme == "https" else 80)


def _field(payload, name):
    value = payload.get(name) if isinstance(payload, dict) else None
    if not isinstance(value, str) or not value:
        raise RuntimeError(f"MinerU V1 response missing {name}")
    return value


def _json(response):
    if not response.is_success:
        raise RuntimeError(f"MinerU V1 HTTP {response.status_code}: {response.text}")
    try:
        payload = response.json()
    except ValueError as exc:
        raise RuntimeError("MinerU V1 returned invalid JSON") from exc
    if not isinstance(payload, dict):
        raise RuntimeError("MinerU V1 returned invalid JSON")
    return payload


class MineruV1:
    def __init__(self, base_url, config, *, task_timeout, poll_interval, transfer_timeout, logger):
        self.base_url = base_url.rstrip("/")
        self.config = config
        self.task_timeout = task_timeout
        self.poll_interval = poll_interval
        self.transfer_timeout = transfer_timeout
        self.logger = logger

    def _request(self, method, path, **kwargs):
        url = urljoin(self.base_url + "/", path)
        target_origin = _origin(url)
        headers = dict(kwargs.pop("headers", {}) or {})
        if self.config.api_key and target_origin == _origin(self.base_url):
            headers.setdefault("Authorization", f"Bearer {self.config.api_key}")
        # Never forward a bearer key through an upload redirect.
        return method, url, {"headers": headers, "follow_redirects": False, **kwargs}

    def job_payload(self, document, file_id):
        backend = self.config.backend
        native = document.suffix.lower() in NATIVE_SUFFIXES
        if native:
            tier = "flash"
        elif backend in TIERS:
            tier = backend
        elif backend == "pipeline":
            tier = "basic"
        else:
            tier = "advanced" if backend.startswith("hybrid-") and self.config.effort == "high" else "standard"
        entry = {"source": {"type": "file_id", "file_id": file_id}}
        if document.suffix.lower() == ".pdf":
            start, end = self.config.start_page_id, self.config.end_page_id
            if start < 0 or end < start:
                raise ValueError("MinerU page range must satisfy 0 <= start_page_id <= end_page_id")
            # The old inclusive zero-based sentinel means through the last page.
            entry["page_range"] = ("all" if start == 0 else f"{start + 1}-r1") if end == 99999 else f"{start + 1}-{end + 1}"
        return {"files": [entry], "tier": tier, "ocr_mode": self.config.parse_method, "output_formats": ["zip"]}

    def _flow(self, document):
        health_response = yield self._request("GET", "v1/health")
        if health_response.status_code in {404, 405}:
            return None
        health = _json(health_response)
        features = health.get("features", {})
        if not isinstance(features, dict):
            raise RuntimeError("MinerU V1 response has invalid features")
        if "zip" not in (features.get("output_formats") or []):
            raise RuntimeError("MinerU V1 service does not support ZIP output required for Markdown and images")
        if "file_id" not in (features.get("sources") or []):
            raise RuntimeError("MinerU V1 service does not support uploaded file sources")
        self.logger.info("检测到 MinerU V1，使用 4.x 上传及解析任务协议")
        if (not self.config.formula_enable or not self.config.table_enable
                or not self.config.image_analysis or self.config.server_url or self.config.lang_list):
            self.logger.warning("MinerU 4.x 不接受旧版公式/表格/图像/语言/模型地址参数；这些选项由服务端配置及解析档位决定")
        # Validate page selection before creating a remote resource.
        self.job_payload(document, "pending")
        response = yield self._request("POST", "v1/uploads", json={
            "filename": document.name, "bytes": len(document.content),
            "mime_type": mimetypes.guess_type(document.name)[0] or "application/octet-stream",
            "purpose": "parse", "sha256sum": hashlib.sha256(document.content).hexdigest(),
        })
        upload = _json(response)
        upload_id = quote(_field(upload, "id"), safe="")
        if upload.get("status") == "pending":
            method = upload.get("upload_method") or "PUT"
            if method != "PUT":
                raise RuntimeError(f"MinerU V1 unsupported upload method: {method}")
            response = yield self._request(method, _field(upload, "upload_url"),
                headers=upload.get("upload_headers"), content=document.content, timeout=self.transfer_timeout)
            if not response.is_success:
                raise RuntimeError(f"MinerU V1 byte upload failed: HTTP {response.status_code}")
            response = yield self._request("POST", f"v1/uploads/{upload_id}/complete", json={})
            upload = _json(response)
        if upload.get("status") != "completed":
            raise RuntimeError("MinerU V1 upload did not complete")
        file_id = _field(upload.get("file"), "id")
        response = yield self._request("POST", "v1/parse/jobs", json=self.job_payload(document, file_id))
        job = _json(response)
        job_id = quote(_field(job, "job_id"), safe="")
        deadline = time.monotonic() + self.task_timeout
        while job.get("status") in {"queued", "running"}:
            if time.monotonic() >= deadline:
                raise TimeoutError(f"MinerU V1 job {job_id} exceeded {self.task_timeout} seconds")
            yield min(self.poll_interval, max(0, deadline - time.monotonic()))
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError(f"MinerU V1 job {job_id} exceeded {self.task_timeout} seconds")
            response = yield self._request("GET", f"v1/parse/jobs/{job_id}", timeout=remaining)
            job = _json(response)
        if job.get("status") != "completed":
            raise RuntimeError(f"MinerU V1 job {job_id} status={job.get('status')}: {job.get('files', [])}")
        files = job.get("files")
        if (not isinstance(files, list) or len(files) != 1
                or not isinstance(files[0], dict) or files[0].get("status") != "completed"):
            raise RuntimeError("MinerU V1 job has no completed file result")
        outputs = files[0].get("output_files")
        if not isinstance(outputs, dict):
            raise RuntimeError("MinerU V1 response has invalid output_files")
        output = outputs.get("zip")
        result_id = quote(_field(output, "file_id"), safe="")
        response = yield self._request("GET", f"v1/files/{result_id}/content", timeout=self.transfer_timeout)
        for _ in range(5):
            if not response.is_redirect:
                break
            location = response.headers.get("location")
            if not location:
                raise RuntimeError("MinerU V1 download redirect missing Location")
            target = urljoin(str(response.url), location)
            # Re-evaluate every hop: same-origin downloads may require auth,
            # but object-store redirects must not receive the service key.
            response = yield self._request("GET", target, timeout=self.transfer_timeout)
        if response.is_redirect:
            raise RuntimeError("MinerU V1 ZIP download exceeded redirect limit")
        if not response.is_success:
            raise RuntimeError(f"MinerU V1 ZIP download failed: HTTP {response.status_code}")
        return response.content

    def run(self, client, document):
        flow, response = self._flow(document), None
        try:
            while True:
                action = flow.send(response)
                if isinstance(action, (float, int)):
                    time.sleep(action)
                    response = None
                else:
                    method, url, kwargs = action
                    response = client.request(method, url, **kwargs)
        except StopIteration as result:
            return result.value
        finally:
            flow.close()

    async def run_async(self, client, document):
        flow, response = self._flow(document), None
        try:
            while True:
                try:
                    action = flow.send(response)
                except StopIteration as result:
                    return result.value
                if isinstance(action, (float, int)):
                    await asyncio.sleep(action)
                    response = None
                else:
                    method, url, kwargs = action
                    response = await client.request(method, url, **kwargs)
        finally:
            flow.close()
