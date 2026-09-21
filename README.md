# InterviewQuestions

Minimal AI wrapper for researching company interview questions with TTL cache.

## What it does
- Supports `chatgpt`, `claude`, and `gemini` provider labels.
- Builds a prompt harness that asks for deep research + web search interview-question samples.
- Uses SQLite cache with TTL to reuse prior results and avoid re-requesting.
- Allows explicit refresh to bypass cache.

## Quick usage
```python
from ai_wrapper import InterviewQuestionService

service = InterviewQuestionService(ttl_seconds=3600)

def requester(provider: str, prompt: str) -> str:
    # Plug in actual provider API call here.
    return f"[{provider}]\n" + prompt

result = service.get_interview_questions("OpenAI", "chatgpt", requester)
print(result.source)      # provider or cache
print(result.questions)
```

Cache database defaults to `interview_questions_cache.db` in the working directory.
