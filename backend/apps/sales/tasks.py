import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task
def decrement_inventory_on_sale(sale_id: str):
    logger.info("decrement_inventory_on_sale task called for sale %s", sale_id)
