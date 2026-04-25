import json
import os
import socket
import subprocess
import tempfile
import time
from pathlib import Path
from urllib import error, request


class OllamaClient:
    def __init__(self, base_url: str | None = None, model: str | None = None):
        self.provider = os.environ.get("KAI_PROVIDER", "ollama").strip().lower() or "ollama"
        env_base_url = os.environ.get("OLLAMA_HOST", "").strip()
        resolved_base_url = base_url or env_base_url or "http://127.0.0.1:11434"
        self.base_url = resolved_base_url.rstrip("/")
        env_model = os.environ.get("KAI_MODEL", "").strip()
        default_models = ["llama3.2:3b", "deepseek-r1:1.5b", "mistral:latest", "llama2:latest"]
        self.model = model or env_model or default_models[0]
        self.default_timeout = int(os.environ.get("KAI_OLLAMA_TIMEOUT", "180"))
        self.temperature = float(os.environ.get("KAI_TEMPERATURE", "0.7"))
        self.repeat_penalty = float(os.environ.get("KAI_REPEAT_PENALTY", "1.15"))
        self.num_predict = int(os.environ.get("KAI_NUM_PREDICT", "512"))
        self.num_ctx = int(os.environ.get("KAI_NUM_CTX", "4096"))
        self.model_inventory_ttl = int(os.environ.get("KAI_MODEL_INVENTORY_TTL", "15"))
        self._model_inventory_cache: tuple[float, list[str]] | None = None
        self.codex_reasoning_effort = os.environ.get("KAI_CODEX_REASONING_EFFORT", "low").strip() or "low"
        self.codex_sandbox = os.environ.get("KAI_CODEX_SANDBOX", "read-only").strip() or "read-only"
        # Hugging Face config — env var only, no hardcoded keys
        self.hf_api_key = (
            os.environ.get("HF_API_KEY", "").strip()
            or os.environ.get("HUGGINGFACE_API_KEY", "").strip()
            or os.environ.get("HUGGINGFACE_HUB_TOKEN", "").strip()
        )
        )
        self.hf_base_url = os.environ.get("HF_API_URL", "https://api-inference.huggingface.co").rstrip("/")
        # DeepSeek config — env var first, then local kai_config.json, then empty
        self.deepseek_api_key = (
            os.environ.get("DEEPSEEK_API_KEY", "").strip()
            or os.environ.get("DS_API_KEY", "").strip()
            or self._load_config_key("deepseek_api_key")
        )
        self.deepseek_base_url = os.environ.get("DEEPSEEK_API_URL", "https://api.deepseek.com").rstrip("/")

    def _load_config_key(self, key: str) -> str:
        config_path = Path("kai_config.json")
        if config_path.exists():
            try:
                with config_path.open("r", encoding="utf-8") as f:
                    cfg = json.load(f)
                value = str(cfg.get(key, "")).strip()
                if value:
                    return value
            except Exception:
                pass
        return ""

    def is_reachable(self, timeout: int = 3) -> bool:
        try:
            self.list_models(timeout=timeout)
            return True
        except Exception:
            return False

    def list_models(self, timeout: int = 3) -> list[str]:
        if self.provider in {"codex", "openai-codex", "openai", "huggingface", "hf", "deepseek"}:
            return [self.model]
        now = time.time()
        if self._model_inventory_cache and (now - self._model_inventory_cache[0]) < self.model_inventory_ttl:
            return list(self._model_inventory_cache[1])
        data = self._request_json("/api/tags", timeout=timeout, method="GET")
        models = data.get("models", [])
        names: list[str] = []
        for item in models:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name", "")).strip()
            if name:
                names.append(name)
        self._model_inventory_cache = (now, names)
        return names

    def has_model(self, model: str, timeout: int = 3) -> bool:
        return model in self.list_models(timeout=timeout)

    def chat(self, messages: list[dict], timeout: int | None = None) -> str:
        if timeout is None:
            timeout = self.default_timeout
        if self.provider in {"codex", "openai-codex", "openai"}:
            return self._chat_codex(messages, timeout=timeout)
        if self.provider in {"huggingface", "hf"}:
            return self._chat_huggingface(messages, timeout=timeout)
        if self.provider == "deepseek":
            return self._chat_deepseek(messages, timeout=timeout)
        payload = json.dumps(
            {
                "model": self.model,
                "messages": messages,
                "stream": False,
                "options": {
                    "temperature": self.temperature,
                    "repeat_penalty": self.repeat_penalty,
                    "num_predict": self.num_predict,
                    "num_ctx": self.num_ctx,
                },
            }
        ).encode("utf-8")
        req = request.Request(
            f"{self.base_url}/api/chat",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        data = self._read_json(req, timeout=timeout)
        message = data.get("message", {})
        content = message.get("content", "").strip()
        if not content:
            raise RuntimeError(f"Ollama model `{self.model}` returned an empty response")
        return content

    def _chat_codex(self, messages: list[dict], timeout: int) -> str:
        prompt = self._build_codex_prompt(messages)
        output_path = Path(tempfile.gettempdir()) / f"kai_codex_{os.getpid()}_{int(time.time() * 1000)}.txt"
        command = [
            "codex",
            "exec",
            "--skip-git-repo-check",
            "--sandbox",
            self.codex_sandbox,
            "-m",
            self.model,
            "-c",
            f'model_reasoning_effort="{self.codex_reasoning_effort}"',
            "--output-last-message",
            str(output_path),
            prompt,
        ]
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=timeout,
                encoding="utf-8",
                errors="replace",
            )
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError(
                f"Codex request timed out after {timeout}s for model `{self.model}`"
            ) from exc
        if result.returncode != 0:
            stderr = (result.stderr or "").strip()
            stdout = (result.stdout or "").strip()
            detail = stderr or stdout or f"exit code {result.returncode}"
            raise RuntimeError(f"Codex request failed for model `{self.model}`: {detail[:600]}")
        if not output_path.exists():
            raise RuntimeError(f"Codex request for model `{self.model}` returned no output file")
        content = output_path.read_text(encoding="utf-8", errors="replace").strip()
        try:
            output_path.unlink(missing_ok=True)
        except Exception:
            pass
        if not content:
            raise RuntimeError(f"Codex model `{self.model}` returned an empty response")
        return content

    def _build_codex_prompt(self, messages: list[dict]) -> str:
        lines = [
            "You are Kai's remote chat backend.",
            "Stay in chat mode only.",
            "Do not run tools.",
            "Do not inspect files.",
            "Do not mention Codex, plugins, sandboxing, or internal execution.",
            "Answer naturally as Kai, based on the conversation below.",
            "",
            "Conversation:",
        ]
        for message in messages:
            role = str(message.get("role", "user")).strip().lower()
            content = str(message.get("content", "")).strip()
            if not content:
                continue
            label = {
                "system": "System",
                "assistant": "Kai",
                "user": "User",
            }.get(role, "User")
            lines.append(f"{label}: {content}")
        lines.extend(["", "Reply as Kai in 1-3 short paragraphs."])
        return "\n".join(lines)

    def _chat_huggingface(self, messages: list[dict], timeout: int) -> str:
        if not self.hf_api_key:
            raise RuntimeError(
                "Hugging Face provider selected but no API key found. "
                "Set HF_API_KEY, HUGGINGFACE_API_KEY, or HUGGINGFACE_HUB_TOKEN environment variable."
            )
        prompt = self._hf_format_prompt(messages)

        # Try multiple endpoint strategies
        strategies = [
            # 1. TGI OpenAI-compatible chat completions
            (
                f"{self.hf_base_url}/models/{self.model}/v1/chat/completions",
                json.dumps({
                    "model": self.model,
                    "messages": messages,
                    "max_tokens": self.num_predict,
                    "temperature": self.temperature,
                    "stream": False,
                }).encode("utf-8"),
                "tgi",
            ),
            # 2. Serverless Inference API (direct model)
            (
                f"{self.hf_base_url}/models/{self.model}",
                json.dumps({
                    "inputs": prompt,
                    "parameters": {
                        "max_new_tokens": self.num_predict,
                        "temperature": self.temperature,
                        "return_full_text": False,
                    },
                }).encode("utf-8"),
                "serverless",
            ),
            # 3. Pipeline API (older format for text-generation)
            (
                f"{self.hf_base_url}/pipeline/text-generation/{self.model}",
                json.dumps({
                    "inputs": prompt,
                    "parameters": {
                        "max_new_tokens": self.num_predict,
                        "temperature": self.temperature,
                        "return_full_text": False,
                    },
                }).encode("utf-8"),
                "pipeline",
            ),
        ]

        for url, payload, strategy in strategies:
            req = request.Request(
                url,
                data=payload,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.hf_api_key}",
                },
                method="POST",
            )
            try:
                with request.urlopen(req, timeout=timeout) as response:
                    data = json.loads(response.read().decode("utf-8"))

                if strategy == "tgi":
                    choices = data.get("choices", [])
                    if choices:
                        content = str(choices[0].get("message", {}).get("content", "")).strip()
                        if content:
                            return content
                else:
                    if isinstance(data, list) and data:
                        content = str(data[0].get("generated_text", "")).strip()
                    elif isinstance(data, dict):
                        content = str(data.get("generated_text", data.get("text", ""))).strip()
                    else:
                        content = ""
                    if content:
                        return content

            except error.HTTPError as exc:
                if exc.code == 404:
                    continue  # Try next strategy
                detail = ""
                try:
                    detail = exc.read().decode("utf-8").strip()
                except Exception:
                    pass
                if exc.code == 401:
                    raise RuntimeError("Hugging Face API key is invalid or expired") from exc
                if exc.code == 503:
                    raise RuntimeError(
                        f"Hugging Face model `{self.model}` is currently loading or unavailable. "
                        "Try again in a few seconds, or use a different model."
                    ) from exc
                if exc.code == 429:
                    raise RuntimeError(
                        "Hugging Face rate limit exceeded. Free tier has limits — wait a moment or upgrade."
                    ) from exc
                raise RuntimeError(f"Hugging Face HTTP error {exc.code}: {detail[:500]}") from exc
            except error.URLError as exc:
                raise RuntimeError(f"Hugging Face API is not reachable: {exc.reason}") from exc
            except TimeoutError as exc:
                raise RuntimeError(
                    f"Hugging Face request timed out after {timeout}s for model `{self.model}`"
                ) from exc

        # All strategies exhausted
        raise RuntimeError(
            f"Hugging Face model `{self.model}` is not available on the free Inference API. "
            f"Model may require a Pro subscription, be gated, or the ID may be incorrect. "
            f"Try models like `gpt2`, `microsoft/DialoGPT-medium`, or check "
            f"https://huggingface.co/models?inference=warm for available models."
        )

    def _hf_format_prompt(self, messages: list[dict]) -> str:
        parts = []
        for msg in messages:
            role = str(msg.get("role", "user")).lower()
            content = str(msg.get("content", "")).strip()
            if role == "system":
                parts.append("### System:\n" + content + "\n")
            elif role == "user":
                parts.append("### User:\n" + content + "\n")
            elif role == "assistant":
                parts.append("### Assistant:\n" + content + "\n")
        parts.append("### Assistant:\n")
        return "\n".join(parts)

    def _chat_deepseek(self, messages: list[dict], timeout: int) -> str:
        if not self.deepseek_api_key:
            raise RuntimeError(
                "DeepSeek provider selected but no API key found. "
                "Set DEEPSEEK_API_KEY or DS_API_KEY environment variable. "
                "Get a key at https://platform.deepseek.com/api_keys"
            )
        url = self.deepseek_base_url + "/chat/completions"
        payload = json.dumps({
            "model": self.model or "deepseek-chat",
            "messages": messages,
            "max_tokens": self.num_predict,
            "temperature": self.temperature,
            "stream": False,
        }).encode("utf-8")
        req = request.Request(
            url,
            data=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer " + self.deepseek_api_key,
            },
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=timeout) as response:
                data = json.loads(response.read().decode("utf-8"))
        except error.HTTPError as exc:
            detail = ""
            try:
                detail = exc.read().decode("utf-8").strip()
            except Exception:
                pass
            if exc.code == 401:
                raise RuntimeError("DeepSeek API key is invalid or expired. Check your key at https://platform.deepseek.com/api_keys") from exc
            if exc.code == 429:
                raise RuntimeError("DeepSeek rate limit exceeded. Wait a moment or check your tier limits.") from exc
            if exc.code in (500, 502, 503):
                raise RuntimeError("DeepSeek server error (" + str(exc.code) + "). Their API may be temporarily overloaded.") from exc
            raise RuntimeError("DeepSeek HTTP error " + str(exc.code) + ": " + detail[:500]) from exc
        except error.URLError as exc:
            raise RuntimeError("DeepSeek API is not reachable: " + str(exc.reason)) from exc
        except TimeoutError as exc:
            raise RuntimeError("DeepSeek request timed out after " + str(timeout) + "s") from exc

        choices = data.get("choices", [])
        if not choices:
            raise RuntimeError("DeepSeek model `" + self.model + "` returned empty choices")
        content = str(choices[0].get("message", {}).get("content", "")).strip()
        if not content:
            raise RuntimeError("DeepSeek model `" + self.model + "` returned an empty response")
        return content

    def set_provider(self, provider: str, model: str | None = None) -> str:
        provider = provider.strip().lower()
        supported = {"ollama", "huggingface", "hf", "deepseek", "codex", "openai-codex", "openai"}
        if provider not in supported:
            return "Unknown provider '" + provider + "'. Supported: " + ", ".join(sorted(supported))
        old = self.provider
        old_model = self.model
        self.provider = provider
        if provider in {"huggingface", "hf"}:
            self.provider = "huggingface"
        if model:
            self.model = model
        else:
            # Set sensible default model when switching providers if current model looks wrong
            if self.provider == "huggingface" and "/" not in self.model:
                self.model = "microsoft/Phi-3-mini-4k-instruct"
            elif self.provider == "deepseek" and not self.model.startswith("deepseek-"):
                self.model = "deepseek-chat"
            elif self.provider in {"codex", "openai-codex", "openai"} and self.model.startswith("ollama-"):
                self.model = "gpt-4o-mini"
        changed_model = " (model: " + self.model + ")" if self.model != old_model else ""
        return "Switched from " + old + " to " + self.provider + changed_model

    def set_model(self, model: str) -> str:
        old = self.model
        self.model = model
        self._model_inventory_cache = None
        return "Model changed from " + old + " to " + self.model

    def _request_json(self, path: str, timeout: int, method: str = "GET") -> dict:
        req = request.Request(self.base_url + path, method=method)
        return self._read_json(req, timeout=timeout)

    def _read_json(self, req: request.Request, timeout: int) -> dict:
        try:
            with request.urlopen(req, timeout=timeout) as response:
                data = json.loads(response.read().decode("utf-8"))
        except error.HTTPError as exc:
            detail = ""
            try:
                detail = exc.read().decode("utf-8").strip()
            except Exception:
                detail = ""
            message = "Ollama HTTP error " + str(exc.code)
            if detail:
                message = message + ": " + detail
            raise RuntimeError(message) from exc
        except TimeoutError as exc:
            raise RuntimeError(
                "Ollama request to " + self.base_url + " timed out after " + str(timeout) + "s for model `" + self.model + "`"
            ) from exc
        except socket.timeout as exc:
            raise RuntimeError(
                "Ollama request to " + self.base_url + " timed out after " + str(timeout) + "s for model `" + self.model + "`"
            ) from exc
        except error.URLError as exc:
            raise RuntimeError("Ollama is not reachable on " + self.base_url) from exc
        return data

