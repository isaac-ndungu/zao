import json
import logging

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from django.conf import settings

logger = logging.getLogger(__name__)

ROLE_MAP = {'user': 'user', 'assistant': 'model'}


@retry(
    retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError)),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=0.5, min=0.5, max=2),
    reraise=True,
)
def _call_gemini(payload: dict) -> dict:
    url = (
        'https://generativelanguage.googleapis.com/v1beta/models/'
        f'{settings.GOOGLE_AI_MODEL}:generateContent'
    )
    with httpx.Client(timeout=settings.GOOGLE_AI_TIMEOUT) as client:
        resp = client.post(
            url,
            json=payload,
            headers={
                'Content-Type': 'application/json',
                'x-goog-api-key': settings.GOOGLE_API_KEY,
            },
        )
        resp.raise_for_status()
        return resp.json()


def ask_gemini(messages: list[dict]) -> str:
    system_prompt = None
    contents = []
    for msg in messages:
        if msg['role'] == 'system':
            system_prompt = msg['content']
        else:
            contents.append({
                'role': ROLE_MAP.get(msg['role'], 'user'),
                'parts': [{'text': msg['content']}],
            })

    payload = {'contents': contents}
    if system_prompt:
        payload['system_instruction'] = {'parts': [{'text': system_prompt}]}

    payload['generationConfig'] = {
        'temperature': settings.GOOGLE_AI_TEMPERATURE,
        'maxOutputTokens': settings.GOOGLE_AI_MAX_TOKENS,
    }

    try:
        result = _call_gemini(payload)
        return result['candidates'][0]['content']['parts'][0]['text']
    except httpx.HTTPStatusError as e:
        logger.error('Gemini HTTP error: %s %s', e.response.status_code, e.response.text[:200])
        raise
    except (httpx.TimeoutException, httpx.NetworkError) as e:
        logger.error('Gemini network error after retries: %s', e)
        raise
    except (KeyError, json.JSONDecodeError) as e:
        logger.error('Gemini response parse failed: %s', e)
        raise RuntimeError('Failed to parse AI response') from e
