import logging

from django.apps import AppConfig

logger = logging.getLogger(__name__)


class BaseConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.base'

    def ready(self):
        from django.apps import apps as django_apps
        from apps.base.models import CooperativeScopedModel, _find_cooperative_fk

        for model in django_apps.get_models():
            if not issubclass(model, CooperativeScopedModel):
                continue
            if model._meta.abstract:
                continue
            if getattr(model, '_cascade_exclude', False):
                continue
            fk_field = _find_cooperative_fk(model)
            if fk_field is None:
                continue
            if fk_field.null:
                logger.warning(
                    '%s.%s is nullable — cascade soft-delete will skip rows '
                    'where %s is NULL. Verify this is intended.',
                    model.__name__, fk_field.name, fk_field.name,
                )
            CooperativeScopedModel._registry.append((model, fk_field.name))

        from django.contrib.auth import get_user_model
        from apps.farmers.models import FarmerCooperativeMembership
        User = get_user_model()
        for model_cls in (User, FarmerCooperativeMembership):
            fk_field = _find_cooperative_fk(model_cls)
            if fk_field is not None:
                already_registered = any(
                    cls is model_cls for cls, _ in CooperativeScopedModel._registry
                )
                if not already_registered:
                    CooperativeScopedModel._registry.append((model_cls, fk_field.name))
