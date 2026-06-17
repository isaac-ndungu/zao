from functools import lru_cache
from typing import Any

from django.conf import settings


@lru_cache(maxsize=1)
def build_api_context() -> list[dict[str, Any]]:
    from drf_spectacular.generators import SchemaGenerator

    generator = SchemaGenerator()
    schema = generator.get_schema(request=None, public=True)
    paths = schema.get('paths', {})

    endpoints = []
    for path, methods in sorted(paths.items()):
        if path.startswith('/api/admin/'):
            continue

        for method in ('get', 'post', 'put', 'patch', 'delete'):
            details = methods.get(method)
            if not details:
                continue

            tags = details.get('tags', [])
            summary = details.get('summary', '') or details.get('operationId', '')
            description = details.get('description', '')
            parameters = _extract_parameters(details)
            request_body = _extract_request_body(details, schema)

            endpoints.append({
                'method': method.upper(),
                'path': path,
                'tags': tags,
                'summary': summary,
                'description': description,
                'parameters': parameters,
                'request_body': request_body,
            })

    return endpoints


def _extract_parameters(details: dict) -> list[dict[str, Any]]:
    params = []
    for param in details.get('parameters', []):
        param_schema = param.get('schema', {})
        params.append({
            'name': param['name'],
            'in': param.get('in', 'query'),
            'type': param_schema.get('type', 'string'),
            'required': param.get('required', False),
            'description': param.get('description', ''),
            'enum': param_schema.get('enum'),
        })
    return params


def _extract_request_body(details: dict, schema: dict) -> list[dict[str, Any]] | None:
    request_body = details.get('requestBody')
    if not request_body:
        return None

    content = request_body.get('content', {})
    json_content = content.get('application/json', {})
    schema_ref = json_content.get('schema', {})

    props = _resolve_properties(schema_ref, schema)
    if props is None:
        return None

    result = []
    required_fields = schema_ref.get('required', [])
    for name, prop_schema in sorted(props.items()):
        result.append({
            'name': name,
            'type': prop_schema.get('type', 'string'),
            'required': name in required_fields,
            'description': prop_schema.get('description', ''),
            'format': prop_schema.get('format', ''),
            'enum': prop_schema.get('enum'),
            'read_only': prop_schema.get('read_only', False),
        })
    return result


def _resolve_properties(schema_ref: dict, full_schema: dict) -> dict | None:
    ref = schema_ref.get('$ref')
    if ref:
        resolved = _resolve_ref(ref, full_schema)
        if resolved:
            return resolved.get('properties')

    if 'properties' in schema_ref:
        return schema_ref['properties']

    additional = schema_ref.get('additionalProperties', {})
    if additional and isinstance(additional, dict):
        return additional.get('properties') or {'value': {'type': 'object'}}

    all_of = schema_ref.get('allOf', [])
    for subschema in all_of:
        ref = subschema.get('$ref')
        if ref:
            resolved = _resolve_ref(ref, full_schema)
            if resolved and 'properties' in resolved:
                return resolved['properties']

    return None


def _resolve_ref(ref: str, full_schema: dict) -> dict | None:
    path = ref.lstrip('#/').split('/')
    obj = full_schema
    for key in path:
        if isinstance(obj, dict):
            obj = obj.get(key)
        else:
            return None
    return obj


def format_endpoints_as_markdown(endpoints: list[dict]) -> str:
    lines = ['## API Endpoints\n']
    current_tag = None

    for ep in endpoints:
        tag = ep['tags'][0] if ep['tags'] else 'General'

        if tag != current_tag:
            lines.append(f'### {tag}\n')
            current_tag = tag

        lines.append(f'**{ep["method"]} `{ep["path"]}`**')
        if ep['summary']:
            lines.append(f': {ep["summary"]}')
        lines.append('\n')

        if ep['description'] and ep['description'] != ep['summary']:
            lines.append(f'> {ep["description"]}\n')

        if ep['parameters']:
            lines.append('> Query parameters:\n')
            for p in ep['parameters']:
                required = ' **required**' if p['required'] else ''
                enum = f' enum: {", ".join(p["enum"])}' if p['enum'] else ''
                lines.append(f'> - `{p["name"]}` ({p["type"]}{required}){enum}\n')

        if ep['request_body']:
            lines.append('> Request body:\n')
            lines.append('> | Field | Type | Required | Notes |\n')
            lines.append('> |---|---|---|---|\n')
            for f in ep['request_body']:
                if f['read_only']:
                    continue
                required = 'yes' if f['required'] else 'no'
                notes = ''
                if f['enum']:
                    notes = f'enum: {", ".join(f["enum"])}'
                elif f['format']:
                    notes = f'format: {f["format"]}'
                elif f['description']:
                    notes = f['description']
                lines.append(f'> | `{f["name"]}` | {f["type"]} | {required} | {notes} |\n')

        lines.append('\n')

    return ''.join(lines)


def build_context_string() -> str:
    endpoints = build_api_context()
    return format_endpoints_as_markdown(endpoints)
