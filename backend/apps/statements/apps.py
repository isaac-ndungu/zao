import logging

from django.apps import AppConfig

logger = logging.getLogger(__name__)


class StatementsConfig(AppConfig):
    name = 'apps.statements'

    def ready(self):
        try:
            from weasyprint import HTML
            HTML(string='<p>startup check</p>').write_pdf(None)
        except Exception as e:
            logger.critical(
                'WeasyPrint startup check FAILED: %s. '
                'PDF generation will fail. '
                'Ensure libpango, libcairo, and libgdk-pixbuf are installed.',
                e,
            )
