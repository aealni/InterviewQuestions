import tempfile
import time
import unittest
from pathlib import Path

from ai_wrapper import InterviewQuestionService


class InterviewQuestionServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp.name) / "cache.db"
        self.service = InterviewQuestionService(db_path=self.db_path, ttl_seconds=60)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_prompt_contains_company_and_research_directive(self) -> None:
        prompt = self.service.build_research_prompt("OpenAI")
        self.assertIn("OpenAI", prompt)
        self.assertIn("deep research", prompt.lower())
        self.assertIn("web search", prompt.lower())

    def test_cache_hit_uses_cached_value(self) -> None:
        calls = []

        def requester(provider: str, prompt: str) -> str:
            calls.append((provider, prompt))
            return "Q1?\nQ2?"

        first = self.service.get_interview_questions("Stripe", "chatgpt", requester)
        second = self.service.get_interview_questions("Stripe", "chatgpt", requester)

        self.assertEqual(first.source, "provider")
        self.assertEqual(second.source, "cache")
        self.assertEqual(len(calls), 1)

    def test_expired_cache_requests_again(self) -> None:
        calls = []

        def requester(provider: str, prompt: str) -> str:
            calls.append((provider, prompt))
            return f"call-{len(calls)}"

        short_ttl = InterviewQuestionService(db_path=self.db_path, ttl_seconds=1)
        first = short_ttl.get_interview_questions("Meta", "claude", requester)
        time.sleep(1.1)
        second = short_ttl.get_interview_questions("Meta", "claude", requester)

        self.assertEqual(first.source, "provider")
        self.assertEqual(second.source, "provider")
        self.assertEqual(second.questions, "call-2")
        self.assertEqual(len(calls), 2)

    def test_force_refresh_bypasses_cache(self) -> None:
        calls = []

        def requester(provider: str, prompt: str) -> str:
            calls.append((provider, prompt))
            return f"refresh-{len(calls)}"

        self.service.get_interview_questions("Nvidia", "gemini", requester)
        refreshed = self.service.get_interview_questions(
            "Nvidia", "gemini", requester, force_refresh=True
        )

        self.assertEqual(refreshed.source, "provider")
        self.assertEqual(refreshed.questions, "refresh-2")
        self.assertEqual(len(calls), 2)

    def test_unsupported_provider_rejected(self) -> None:
        with self.assertRaises(ValueError):
            self.service.get_interview_questions(
                "Google",
                "bing",
                lambda provider, prompt: "unused",
            )


if __name__ == "__main__":
    unittest.main()
