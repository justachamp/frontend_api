from rest_framework_json_api.utils import get_included_resources
from rest_framework_json_api.views import AutoPrefetchMixin
from rest_framework_json_api import views


class ModelViewSet(views.ModelViewSet):
    def get_queryset(self, *args, **kwargs):
        from django.db.models.fields.related_descriptors import (
            ForwardManyToOneDescriptor,
            ManyToManyDescriptor,
            ReverseManyToOneDescriptor,
            ReverseOneToOneDescriptor
        )

        """ This mixin adds automatic prefetching for OneToOne and ManyToMany fields. """
        qs = super(AutoPrefetchMixin, self).get_queryset(*args, **kwargs)
        included_resources = get_included_resources(self.request)

        for included in included_resources:
            included_model = None
            levels = included.split('.')
            level_model = qs.model
            for level in levels:
                if not hasattr(level_model, level):
                    break
                field = getattr(level_model, level)
                field_class = field.__class__

                is_forward_relation = (
                        issubclass(field_class, ForwardManyToOneDescriptor) or
                        issubclass(field_class, ManyToManyDescriptor)
                )
                is_reverse_relation = (
                        issubclass(field_class, ReverseManyToOneDescriptor) or
                        issubclass(field_class, ReverseOneToOneDescriptor)
                )
                if not (is_forward_relation or is_reverse_relation):
                    break

                if level == levels[-1]:
                    included_model = field
                else:
                    has_field = getattr(field, 'field', False)
                    if has_field:
                        model_field = field.field
                    else:
                        model_field = field.related

                    if is_forward_relation or not has_field:
                        level_model = model_field.related_model
                    else:
                        level_model = model_field.model

            if included_model is not None:
                qs = qs.prefetch_related(included.replace('.', '__'))

        return qs