from memengine.memory.BaseMemory import ExplicitMemory
from types import SimpleNamespace
import time


class ZepMemory(ExplicitMemory):
    def __init__(self, config) -> None:
        super().__init__(config)

        try:
            from zep_cloud.client import Zep
            from zep_cloud.types import Message
        except ImportError as exc:
            raise ImportError(
                "zep-cloud is not installed in the current environment."
            ) from exc

        self.ZepMessage = Message
        self.api_key = self.config.args.zep.api_key
        self.user_id = self.config.args.zep.user_id
        self.session_id = self.config.args.zep.session_id
        # self.top_k = getattr(self.config.args.zep, "top_k", 5)
        self.max_query_chars = getattr(self.config.args.zep, "max_query_chars", 380)
        self.store_delay_seconds = getattr(self.config.args.zep, "store_delay_seconds", 12)
        self.max_retries = getattr(self.config.args.zep, "max_retries", 5)
        self.retry_fallback_seconds = getattr(self.config.args.zep, "retry_fallback_seconds", 45)
        self.recall_op = SimpleNamespace(last_retrieved_ids=[])
        self.return_context_fallback = getattr(
            self.config.args.zep, "return_context_fallback", "None"
        )

        if not self.api_key:
            raise ValueError("Missing ZEP API key.")

        self.client = Zep(api_key=self.api_key)

        self._ensure_user()
        self._ensure_thread()

    def _ensure_user(self) -> None:
        try:
            self.client.user.add(
                user_id=self.user_id,
                email=f"{self.user_id}@example.com",
                first_name=self.user_id,
                last_name="MemGallery",
            )
        except Exception:
            pass

    def _ensure_thread(self) -> None:
        try:
            self.client.thread.create(
                thread_id=self.session_id,
                user_id=self.user_id,
            )
        except Exception:
            pass

    def reset(self) -> None:
        pass

    # def store(self, observation) -> None:
    #     text = self._observation_to_text(observation)
    #     if not text:
    #         return

    #     message = self.ZepMessage(
    #         name=self.user_id,
    #         role="user",
    #         content=text,
    #     )

    #     self.client.thread.add_messages(
    #         self.session_id,
    #         messages=[message],
    #     )

    def store(self, observation) -> None:
        if not isinstance(observation, dict):
            return

        text = self._observation_to_text(observation)
        if not text:
            return

        # dialogue_id = observation.get("dialogue_id", "")
        # timestamp = observation.get("timestamp", "")
        # session_id = self._normalize_session_id(dialogue_id)

        dialogue_id = str(observation.get("dialogue_id", "")).strip()
        timestamp = observation.get("timestamp", "")
        session_id = str(observation.get("session_id", "")).strip()
        # mem_id = f"{session_id}:{dialogue_id}" if session_id and dialogue_id else dialogue_id
        if dialogue_id and ":" in dialogue_id:
            mem_id = dialogue_id
        elif session_id and dialogue_id:
            mem_id = f"{session_id}:{dialogue_id}"
        else:
            mem_id = dialogue_id

        message = self.ZepMessage(
            name=self.user_id,
            role="user",
            content=text,
            # metadata={
            #     "dialogue_id": dialogue_id,
            #     "mem_gallery_session_id": session_id,
            #     "timestamp": timestamp,
            # },
            metadata={
                "dialogue_id": mem_id,
                "mem_gallery_session_id": session_id,
                "mem_gallery_round_id": dialogue_id,
                "timestamp": timestamp,
            },
            created_at=self._to_rfc3339(timestamp),
        )

        # self.client.thread.add_messages(
        #     self.session_id,
        #     messages=[message],
        # )
        for attempt in range(self.max_retries):
            try:
                self.client.thread.add_messages(
                self.session_id,
                messages=[message],
                )
                time.sleep(self.store_delay_seconds)
                return
            except Exception as e:
                error_text = str(e)
                retry_after = self.retry_fallback_seconds

                if "retry-after" in error_text.lower():
                    import re
                    match = re.search(r"retry-after': '(\d+)'", error_text.lower())
                    if match:
                        retry_after = int(match.group(1))

                if "429" in error_text or "rate limit exceeded" in error_text.lower():
                    time.sleep(retry_after + 1)
                    continue

                raise

        raise RuntimeError(f"Failed to store message after {self.max_retries} retries.")
    
    def _to_rfc3339(self, timestamp: str) -> str | None:
        # 时间格式转换
        if not timestamp:
            return None
        try:
            return f"{timestamp}T00:00:00Z"
        except Exception:
            return None

    def _dedupe_keep_order(self, items):
        # 去重，但保留原顺序
        seen = set()
        result = []
        for item in items:
            item = str(item).strip()
            if item and item not in seen:
                seen.add(item)
                result.append(item)
        return result

    # def recall(self, query) -> str:
    #     query_text = self._observation_to_text(query)
    #     if not query_text:
    #         return self.return_context_fallback

    #     query_message = self.ZepMessage(
    #         name=self.user_id,
    #         role="user",
    #         content=query_text,
    #     )

    #     self.client.thread.add_messages(
    #         self.session_id,
    #         messages=[query_message],
    #     )

    #     user_context = self.client.thread.get_user_context(
    #         thread_id=self.session_id
    #     )

    #     context = getattr(user_context, "context", None)
    #     if context:
    #         return context

    #     if isinstance(user_context, dict) and user_context.get("context"):
    #         return user_context["context"]

    #     return self.return_context_fallback

    def recall(self, query) -> str:
        query_text = self._observation_to_text(query)
        if not query_text:
            self.recall_op.last_retrieved_ids = []
            return self.return_context_fallback
        
        search_query = self._build_search_query(query_text)

        results = self.client.graph.search(
            user_id=self.user_id,
            query=search_query,
            scope="episodes",
            reranker="cross_encoder",
        )

        episodes = getattr(results, "episodes", []) or []

        retrieved_ids = []
        context_chunks = []

        for ep in episodes:
            metadata = getattr(ep, "metadata", {}) or {}
            dialogue_id = metadata.get("dialogue_id")

            if dialogue_id:
                retrieved_ids.append(str(dialogue_id))

            content = getattr(ep, "content", None)
            if content:
                context_chunks.append(content.strip())

        # Mem-Gallery retrieval metrics 读取这个字段
        self.recall_op.last_retrieved_ids = self._dedupe_keep_order(retrieved_ids)

        if context_chunks:
            return "\n\n".join(context_chunks)

        return self.return_context_fallback


    def display(self) -> None:
        pass

    def manage(self, operation, **kwargs) -> None:
        pass

    def optimize(self, **kwargs) -> None:
        pass

    def _observation_to_text(self, observation) -> str:
        if observation is None:
            return ""

        if isinstance(observation, str):
            return observation.strip()

        if isinstance(observation, dict):
            return str(observation.get("text", "")).strip()

        return str(observation).strip()
    
    def _build_search_query(self, query_text: str) -> str:
        if not query_text:
            return ""

        max_len = self.max_query_chars
        text = query_text.strip()

        image_marker = "\nquestion's image:\nimage_caption:"
        if image_marker not in text:
            return text[:max_len]

        question_part, caption_part = text.split(image_marker, 1)
        question_part = question_part.strip()
        caption_part = caption_part.strip()

        if len(question_part) >= max_len:
            return question_part[:max_len]

        remaining = max_len - len(question_part)
        suffix = f"{image_marker} {caption_part}"

        return question_part + suffix[:remaining]