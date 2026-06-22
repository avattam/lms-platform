"""Two-pass LLM assessment grading via Ollama (Qwen3-1.7B)."""
import json

import httpx

from core.config import settings

OLLAMA_GENERATE_URL = f"{settings.OLLAMA_BASE_URL}/api/generate"


async def _ollama_generate(prompt: str) -> str:
    """Call Ollama generate endpoint and return the response text."""
    payload = {
        "model": settings.LLM_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.1},  # low temp for deterministic grading
    }
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(OLLAMA_GENERATE_URL, json=payload)
        resp.raise_for_status()
        return resp.json().get("response", "")


async def grade_free_form(
    student_answer: str,
    rubric: str,
    correct_answer: str,
    max_score: int,
) -> dict:
    """
    Two-pass LLM grading:
    Pass 1 — Extract key semantic concepts from student answer.
    Pass 2 — Compare concepts vs. correct answer, output score + reasoning.
    """

    # --- Pass 1: Concept Extraction ---
    pass1_prompt = f"""You are an educational evaluator.
Given the following rubric and student answer, extract the key semantic concepts present in the student's response.
Output ONLY a JSON array of concept strings. Example: ["concept A", "concept B"]

Rubric: {rubric}
Student Answer: {student_answer}

Output:"""

    pass1_raw = await _ollama_generate(pass1_prompt)

    # Parse concepts safely
    try:
        concepts = json.loads(pass1_raw.strip())
        if not isinstance(concepts, list):
            concepts = []
    except json.JSONDecodeError:
        concepts = [pass1_raw.strip()]

    # --- Pass 2: Grading ---
    pass2_prompt = f"""You are an educational grader.
Compare the extracted student concepts against the correct answer and assign a score.

Correct Answer / Key Concepts: {correct_answer}
Student Extracted Concepts: {json.dumps(concepts)}
Maximum Score: {max_score}

Output ONLY valid JSON in this exact format:
{{"score": <integer 0 to {max_score}>, "reasoning": "<one sentence explanation>"}}

Output:"""

    pass2_raw = await _ollama_generate(pass2_prompt)

    # Parse grading result safely
    try:
        # Extract JSON from response (LLM may add surrounding text)
        start = pass2_raw.find("{")
        end = pass2_raw.rfind("}") + 1
        result = json.loads(pass2_raw[start:end])
        score = max(0, min(int(result.get("score", 0)), max_score))
        reasoning = result.get("reasoning", "No reasoning provided.")
    except (json.JSONDecodeError, ValueError):
        score = 0
        reasoning = f"Could not parse LLM response: {pass2_raw[:200]}"

    return {
        "score": score,
        "reasoning": reasoning,
        "concepts": concepts,
    }
