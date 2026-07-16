import pytest

from zaoapi.settings import _scrub_pii


@pytest.fixture
def base_event():
    return {'breadcrumbs': {'values': []}, 'message': ''}


class TestScrubPII:
    def test_scrubs_phone_in_frame_vars(self, base_event):
        event = {
            'exception': {
                'values': [{
                    'stacktrace': {
                        'frames': [{'vars': {'phone': '+254712345678'}}]
                    }
                }]
            },
            'breadcrumbs': {'values': []},
        }
        result = _scrub_pii(event, None)
        assert result['exception']['values'][0]['stacktrace']['frames'][0]['vars']['phone'] == '[PHONE_SCRUBBED]'

    def test_scrubs_phone_without_plus(self, base_event):
        event = {
            'exception': {
                'values': [{
                    'stacktrace': {
                        'frames': [{'vars': {'phone': '254712345678'}}]
                    }
                }]
            },
            'breadcrumbs': {'values': []},
        }
        result = _scrub_pii(event, None)
        assert result['exception']['values'][0]['stacktrace']['frames'][0]['vars']['phone'] == '[PHONE_SCRUBBED]'

    def test_scrubs_national_id_in_frame_vars(self, base_event):
        event = {
            'exception': {
                'values': [{
                    'stacktrace': {
                        'frames': [{'vars': {'id_number': '12345678'}}]
                    }
                }]
            },
            'breadcrumbs': {'values': []},
        }
        result = _scrub_pii(event, None)
        assert result['exception']['values'][0]['stacktrace']['frames'][0]['vars']['id_number'] == '[ID_SCRUBBED]'

    def test_scrubs_exception_value(self, base_event):
        event = {
            'exception': {
                'values': [{
                    'value': 'User +254712345678 not found',
                    'stacktrace': {'frames': []}
                }]
            },
            'breadcrumbs': {'values': []},
        }
        result = _scrub_pii(event, None)
        assert result['exception']['values'][0]['value'] == 'User [PHONE_SCRUBBED] not found'

    def test_scrubs_breadcrumb_data(self, base_event):
        event = {
            'breadcrumbs': {
                'values': [{
                    'type': 'http',
                    'data': {'url': '/api/farmers/1234567890/', 'method': 'GET'}
                }]
            },
        }
        result = _scrub_pii(event, None)
        assert result['breadcrumbs']['values'][0]['data']['url'] == '/api/farmers/[ID_SCRUBBED]/'

    def test_scrubs_breadcrumb_message(self, base_event):
        event = {
            'breadcrumbs': {
                'values': [{
                    'type': 'default',
                    'message': 'Failed login for +254712345678',
                }]
            },
        }
        result = _scrub_pii(event, None)
        assert result['breadcrumbs']['values'][0]['message'] == 'Failed login for [PHONE_SCRUBBED]'

    def test_scrubs_top_level_message(self, base_event):
        event = {
            'message': 'Error processing payment for ID 12345678',
        }
        result = _scrub_pii(event, None)
        assert result['message'] == 'Error processing payment for ID [ID_SCRUBBED]'

    def test_preserves_non_pii_values(self, base_event):
        event = {
            'exception': {
                'values': [{
                    'stacktrace': {
                        'frames': [{'vars': {'name': 'John', 'age': 30}}]
                    }
                }]
            },
            'breadcrumbs': {'values': []},
        }
        result = _scrub_pii(event, None)
        assert result['exception']['values'][0]['stacktrace']['frames'][0]['vars']['name'] == 'John'
        assert result['exception']['values'][0]['stacktrace']['frames'][0]['vars']['age'] == 30

    def test_handles_no_exception(self, base_event):
        event = {'message': 'Just a log message'}
        result = _scrub_pii(event, None)
        assert result['message'] == 'Just a log message'

    def test_handles_empty_event(self):
        result = _scrub_pii({}, None)
        assert result == {}
