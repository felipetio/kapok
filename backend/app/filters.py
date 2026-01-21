import django_filters

from app.models import Community, Land


class LandFilter(django_filters.FilterSet):
    """Filter for Land model."""

    name = django_filters.CharFilter(lookup_expr="icontains")
    category = django_filters.ChoiceFilter(choices=Land.CATEGORY_CHOICES)

    # Location filters - use annotated fields for better performance
    municipality = django_filters.CharFilter(field_name="municipality__name", lookup_expr="icontains")
    state = django_filters.CharFilter(field_name="municipality__state__name", lookup_expr="icontains")
    state_code = django_filters.CharFilter(field_name="municipality__state__code")
    country = django_filters.CharFilter(field_name="municipality__state__country__name", lookup_expr="icontains")
    country_code = django_filters.CharFilter(field_name="municipality__state__country__code", lookup_expr="iexact")

    # Biome and community filters
    biome = django_filters.CharFilter(field_name="biome__name", lookup_expr="icontains")
    community = django_filters.CharFilter(field_name="communities__name", lookup_expr="icontains")

    # Count filters
    communities_count = django_filters.NumberFilter()
    communities_count_min = django_filters.NumberFilter(field_name="communities_count", lookup_expr="gte")
    communities_count_max = django_filters.NumberFilter(field_name="communities_count", lookup_expr="lte")

    class Meta:
        model = Land
        fields = [
            "name",
            "category",
            "municipality",
            "state",
            "state_code",
            "country",
            "country_code",
            "biome",
            "community",
            "communities_count",
            "communities_count_min",
            "communities_count_max",
        ]


class CommunityFilter(django_filters.FilterSet):
    """Filter for Community model."""

    name = django_filters.CharFilter(lookup_expr="icontains")

    # Count filters
    lands_count = django_filters.NumberFilter()
    lands_count_min = django_filters.NumberFilter(field_name="lands_count", lookup_expr="gte")
    lands_count_max = django_filters.NumberFilter(field_name="lands_count", lookup_expr="lte")

    class Meta:
        model = Community
        fields = ["name", "lands_count", "lands_count_min", "lands_count_max"]
