import json
import logging
from urllib.error import URLError
from urllib.request import Request, urlopen

from django.conf import settings

logger = logging.getLogger(__name__)

ROLE_MAP = {'user': 'user', 'assistant': 'model'}


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

    generation_config = {
        'temperature': settings.GOOGLE_AI_TEMPERATURE,
        'maxOutputTokens': settings.GOOGLE_AI_MAX_TOKENS,
    }
    payload['generationConfig'] = generation_config

    url = (
        'https://generativelanguage.googleapis.com/v1beta/models/'
        f'{settings.GOOGLE_AI_MODEL}:generateContent'
    )

    body = json.dumps(payload).encode('utf-8')
    req = Request(
        url, data=body,
        headers={
            'Content-Type': 'application/json',
            'x-goog-api-key': settings.GOOGLE_API_KEY,
        },
        method='POST',
    )

    try:
        with urlopen(req, timeout=settings.GOOGLE_AI_TIMEOUT) as resp:
            result = json.loads(resp.read().decode('utf-8'))
            return result['candidates'][0]['content']['parts'][0]['text']
    except URLError as e:
        logger.error('Gemini request failed: %s', e)
        raise
    except (KeyError, json.JSONDecodeError) as e:
        logger.error('Gemini response parse failed: %s', e)
        raise RuntimeError('Failed to parse AI response') from e
