from __future__ import annotations

import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

SUPPORTED_PROVIDERS = {"chatgpt", "claude", "gemini"}


@dataclass(frozen=True)
class InterviewQuestionResult:
    company: str
    provider: str
    questions: str
    source: str  # "cache" or "provider"
    fetched_at: int


class InterviewQuestionService:
    def __init__(
        self,
        db_path: str | Path = "interview_questions_cache.db",
        ttl_seconds: int = 60 * 60 * 24,
    ) -> None:
        if ttl_seconds <= 0:
            raise ValueError("ttl_seconds must be positive")
        self.db_path = str(db_path)
        self.ttl_seconds = ttl_seconds
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS interview_questions_cache (
                    company TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    questions TEXT NOT NULL,
                    fetched_at INTEGER NOT NULL,
                    PRIMARY KEY (company, provider)
                )
                """
            )
            conn.commit()

    @staticmethod
    def build_research_prompt(company: str) -> str:
        company_name = company.strip()
        if not company_name:
            raise ValueError("company is required")

        return (
            "You are an interview research harness. Use deep research and web search to gather realistic "
            f"interview question samples for {company_name}. "
            "Return concise, high-signal results grouped by interview stage (screening, technical, behavioral, "
            "system design). Include 3-5 sample questions per stage and mention confidence caveats if data is sparse."
        )

    def get_interview_questions(
        self,
        company: str,
        provider: str,
        requester: Callable[[str, str], str],
        force_refresh: bool = False,
    ) -> InterviewQuestionResult:
        provider_name = provider.strip().lower()
        if provider_name not in SUPPORTED_PROVIDERS:
            raise ValueError(
                f"Unsupported provider '{provider}'. Supported providers: {sorted(SUPPORTED_PROVIDERS)}"
            )

        normalized_company = company.strip()
        if not normalized_company:
            raise ValueError("company is required")

        now = int(time.time())
        if not force_refresh:
            cached = self._get_cached(normalized_company, provider_name, now)
            if cached is not None:
                return InterviewQuestionResult(
                    company=normalized_company,
                    provider=provider_name,
                    questions=cached[0],
                    source="cache",
                    fetched_at=cached[1],
                )

        prompt = self.build_research_prompt(normalized_company)
        questions = requester(provider_name, prompt)
        self._save_cache(normalized_company, provider_name, questions, now)
        return InterviewQuestionResult(
            company=normalized_company,
            provider=provider_name,
            questions=questions,
            source="provider",
            fetched_at=now,
        )

    def _get_cached(self, company: str, provider: str, now: int) -> tuple[str, int] | None:
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                """
                SELECT questions, fetched_at
                FROM interview_questions_cache
                WHERE company = ? AND provider = ?
                """,
                (company, provider),
            ).fetchone()

        if not row:
            return None

        questions, fetched_at = row
        if now - int(fetched_at) < self.ttl_seconds:
            return str(questions), int(fetched_at)
        return None

    def _save_cache(self, company: str, provider: str, questions: str, fetched_at: int) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO interview_questions_cache (company, provider, questions, fetched_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(company, provider)
                DO UPDATE SET questions=excluded.questions, fetched_at=excluded.fetched_at
                """,
                (company, provider, questions, fetched_at),
            )
            conn.commit()
