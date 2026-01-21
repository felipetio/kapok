# Backend Coding Conventions

This document outlines the backend coding conventions and patterns used in the Kapok project. These conventions have been identified through analysis of the existing Python codebase and should be followed for consistency and maintainability.

## How to Use This Document

### Purpose and Scope

These are **conventions, not requirements**. They represent patterns that have emerged organically in our codebase and are documented here to:

- Help new team members understand existing patterns
- Provide guidance for consistent code style
- Serve as a reference during development
- Facilitate more focused code reviews

### In Development

**Use conventions as applicable:**

- Apply patterns that fit your specific use case
- Don't force conventions where they don't make sense
- Prioritize readability and functionality over strict adherence
- Consider the conventions as starting points, not rigid rules

**When to reference this document:**

- Setting up new Django models or API views
- Choosing between different approaches
- Looking for established patterns in the codebase
- Onboarding to unfamiliar areas of the application

### In Code Review

**Conventions are guidance, not blockers:**

- Missing conventions are not automatically problematic
- Focus on correctness, security, and maintainability first
- Suggest conventions when they would improve code clarity
- Consider the context and complexity of the change

**Helpful review approach:**

- "Consider using the established pattern for..."
- "This follows our convention for..."
- "For consistency with similar code..."

### Evolution

These conventions will evolve as the codebase grows. When you notice:

- Repeated patterns not documented here
- Better approaches than what's documented
- Conventions that no longer serve the codebase

Please contribute back to this document or discuss with the team.

## Table of Contents

1. [Core Libraries and Dependencies](#core-libraries-and-dependencies)
2. [Django Models](#django-models)
3. [API Design Patterns](#api-design-patterns)
4. [Testing Patterns](#testing-patterns)
5. [Database Conventions](#database-conventions)
6. [Code Organization](#code-organization)
7. [Admin Customization](#admin-customization)

## Core Libraries and Dependencies

### Essential Dependencies

The following libraries are pervasive throughout the application and should be used consistently:

#### Django Core

- **Django 5.1+**: Main framework
- **django-environ**: Environment variable configuration
- **psycopg2-binary**: PostgreSQL adapter
- **django-redis**: Redis caching backend

#### Django REST Framework

- **djangorestframework**: REST API framework
- **django-filter**: QuerySet filtering
- **drf-spectacular**: OpenAPI 3.0 schema generation

#### Testing

- **pytest**: Testing framework
- **pytest-django**: Django-specific pytest plugins
- **factory-boy**: Test data factories
- **coverage**: Code coverage reporting
- **django-coverage-plugin**: Django template coverage

#### Development Tools

- **black**: Code formatter
- **isort**: Import sorting
- **flake8**: Linting
- **flake8-isort**: isort integration for flake8
- **django-debug-toolbar**: Development debugging
- **django-extensions**: Additional management commands (shell_plus, etc.)

### ✅ Preferred Library Usage

```python
# Use Django's timezone-aware datetime handling
from django.utils import timezone
now = timezone.now()

# Use django-environ for settings
import environ
env = environ.Env()
SECRET_KEY = env('SECRET_KEY')
DATABASE_URL = env.db()

# Use factory-boy for test data
from factory.django import DjangoModelFactory
class LandFactory(DjangoModelFactory):
    class Meta:
        model = Land
    name = factory.Faker('city')
```

### ❌ Avoid These Patterns

```python
# Don't use naive datetime
from datetime import datetime
now = datetime.now()  # Use timezone.now() instead

# Don't hardcode configuration
SECRET_KEY = "hardcoded-secret"  # Use environment variables

# Don't create test data manually in every test
land = Land.objects.create(name="Test")  # Use factories instead
```

## Django Models

### Model Field Patterns

All models in this project use UUID primary keys for better scalability and security:

#### ✅ Correct Model Definition

```python
import uuid
from django.db import models

class Land(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    category = models.CharField(max_length=200, choices=CATEGORY_CHOICES)

    municipality = models.ForeignKey(
        Municipality,
        on_delete=models.CASCADE,
        related_name="lands",
        null=True,
        blank=True,
    )

    # External data integration fields
    source_id = models.CharField(max_length=100, null=True, blank=True, db_index=True)
    source_name = models.CharField(max_length=50, null=True, blank=True)
    source_updated_at = models.DateTimeField(null=True, blank=True)
    source_last_synced_at = models.DateTimeField(null=True, blank=True)
    source_raw_data = models.JSONField(null=True, blank=True)

    class Meta:
        unique_together = [["source_name", "source_id"]]

    def __str__(self):
        return self.name
```

### Model Field Conventions

#### UUID Primary Keys

All models use UUID primary keys:

```python
id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
```

**Rationale:**
- Better for distributed systems
- No sequential ID leakage
- Easier for data synchronization
- Consistent across all models

#### Foreign Key Conventions

Always specify `related_name` for foreign keys:

```python
# ✅ Good - Clear related name
municipality = models.ForeignKey(
    Municipality,
    on_delete=models.CASCADE,
    related_name="lands",  # Clear and descriptive
    null=True,
    blank=True,
)

# ❌ Bad - No related name or using default
municipality = models.ForeignKey(Municipality, on_delete=models.CASCADE)
```

#### External Data Integration Pattern

When integrating with external data sources, use this pattern:

```python
# Source tracking fields
source_id = models.CharField(max_length=100, null=True, blank=True, db_index=True)
source_name = models.CharField(max_length=50, null=True, blank=True)
source_updated_at = models.DateTimeField(null=True, blank=True)
source_last_synced_at = models.DateTimeField(null=True, blank=True)
source_raw_data = models.JSONField(null=True, blank=True)

class Meta:
    unique_together = [["source_name", "source_id"]]
```

**Benefits:**
- Track data lineage
- Enable incremental updates
- Support multiple data sources
- Preserve raw data for debugging

#### Localization Pattern

For models with localized content:

```python
name = models.CharField(max_length=200)
name_local = models.CharField(max_length=200, null=True, blank=True)

description = models.TextField(null=True, blank=True)
description_local = models.TextField(null=True, blank=True)
```

### Model Methods

#### String Representation

Always implement `__str__` for admin and debugging:

```python
def __str__(self):
    return self.name
```

#### Custom Save Methods

When implementing custom save logic, always call super():

```python
def save(self, *args, **kwargs):
    if not self.slug:
        self.slug = slugify(self.name)
    super().save(*args, **kwargs)
```

### Model Meta Options

#### Verbose Names

Use plural forms for models with irregular plurals:

```python
class Meta:
    verbose_name_plural = "Countries"  # Not "Countrys"
```

#### Unique Constraints

Use `unique_together` for composite uniqueness:

```python
class Meta:
    unique_together = [["source_name", "source_id"]]
```

#### Indexing

Add indexes for frequently queried fields:

```python
source_id = models.CharField(max_length=100, db_index=True)
```

## API Design Patterns

### Serializer Structure

Follow consistent patterns for DRF serializers:

#### ✅ Read/Write Separation Pattern

```python
from rest_framework import serializers
from app.models import Land, Biome, Community

class LandSerializer(serializers.ModelSerializer):
    # Read-only nested serializers for related objects
    biome = BiomeSerializer(read_only=True)
    communities = CommunitySerializer(many=True, read_only=True)

    # Write-only primary key fields
    biome_id = serializers.PrimaryKeyRelatedField(
        queryset=Biome.objects.all(),
        source="biome",
        write_only=True
    )
    communities_ids = serializers.PrimaryKeyRelatedField(
        queryset=Community.objects.all(),
        source="communities",
        many=True,
        write_only=True,
    )

    # Computed fields
    category_display = serializers.CharField(
        source="get_category_display",
        read_only=True
    )

    class Meta:
        model = Land
        fields = [
            "id",
            "name",
            "category",
            "category_display",
            "biome",
            "biome_id",
            "communities",
            "communities_ids",
        ]
```

**Rationale:**
- Clear separation between read and write operations
- Rich data in responses (nested objects)
- Simple data in requests (just IDs)
- Avoid circular serialization issues

#### SerializerMethodField Pattern

Use `SerializerMethodField` for complex computed data:

```python
class LandSerializer(serializers.ModelSerializer):
    location = serializers.SerializerMethodField()
    source_link = serializers.SerializerMethodField()

    def get_location(self, obj):
        """Return flattened location information."""
        location = {}

        # Use annotated fields if available (better performance)
        if hasattr(obj, 'municipality_name'):
            location['municipality'] = obj.municipality_name
            location['state'] = obj.state_name
        # Fallback to related objects
        elif obj.municipality:
            location['municipality'] = obj.municipality.name
            if obj.municipality.state:
                location['state'] = obj.municipality.state.name

        return location if location else None

    def get_source_link(self, obj):
        """Return external source link if available."""
        if obj.source_name == "ISA" and obj.source_id:
            return f"https://terrasindigenas.org.br/en/terras-indigenas/{obj.source_id}"
        return None
```

#### Docstrings

Add docstrings to serializers for API documentation:

```python
class CountrySerializer(serializers.ModelSerializer):
    """Serializer for Country model."""

    class Meta:
        model = Country
        fields = ["id", "name", "code"]
```

### ViewSet Patterns

#### ✅ Using ModelViewSet

```python
from rest_framework import viewsets
from app.models import Land
from app.serializers import LandSerializer
from app.filters import LandFilter

class LandViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing indigenous lands.

    Supports filtering by category, biome, municipality, and state.
    """
    queryset = Land.objects.all()
    serializer_class = LandSerializer
    filterset_class = LandFilter

    def get_queryset(self):
        """
        Optimize queryset with select_related and prefetch_related.
        """
        return super().get_queryset().select_related(
            'biome',
            'municipality__state__country'
        ).prefetch_related(
            'communities'
        )
```

### Filtering

Use django-filter for complex filtering:

```python
from django_filters import rest_framework as filters
from app.models import Land

class LandFilter(filters.FilterSet):
    category = filters.ChoiceFilter(choices=Land.CATEGORY_CHOICES)
    biome = filters.ModelChoiceFilter(queryset=Biome.objects.all())
    municipality = filters.ModelChoiceFilter(queryset=Municipality.objects.all())

    class Meta:
        model = Land
        fields = ['category', 'biome', 'municipality']
```

## Testing Patterns

### Factory Pattern

Use factory-boy for consistent test data:

#### ✅ Factory Definition

```python
import factory
from factory.django import DjangoModelFactory
from app.models import Country, State, Land

class CountryFactory(DjangoModelFactory):
    class Meta:
        model = Country

    name = factory.Faker('country')
    code = factory.Faker('country_code')

class StateFactory(DjangoModelFactory):
    class Meta:
        model = State

    name = factory.Faker('state')
    code = factory.Faker('state_abbr')
    country = factory.SubFactory(CountryFactory)

class LandFactory(DjangoModelFactory):
    class Meta:
        model = Land

    name = factory.Faker('city')
    category = "TI"
    municipality = factory.SubFactory(MunicipalityFactory)
    biome = factory.SubFactory(BiomeFactory)
```

### Test Structure

#### ✅ Good Test Structure

```python
import pytest
from app.factories import LandFactory, CountryFactory

@pytest.mark.django_db
class TestLandModel:
    """Tests for the Land model."""

    def test_land_creation(self):
        """Test creating a land with valid data."""
        land = LandFactory(category="TI")
        assert land.category == "TI"
        assert str(land) == land.name

    def test_land_unique_source(self):
        """Test that source_name and source_id must be unique together."""
        LandFactory(source_name="ISA", source_id="123")

        with pytest.raises(Exception):
            LandFactory(source_name="ISA", source_id="123")

@pytest.mark.django_db
class TestLandAPI:
    """Tests for the Land API endpoints."""

    def test_list_lands(self, client):
        """Test listing lands returns all lands."""
        LandFactory.create_batch(5)
        response = client.get('/api/lands/')

        assert response.status_code == 200
        assert len(response.json()) == 5

    def test_filter_lands_by_category(self, client):
        """Test filtering lands by category."""
        LandFactory(category="TI")
        LandFactory(category="RI")

        response = client.get('/api/lands/?category=TI')

        assert response.status_code == 200
        assert len(response.json()) == 1
        assert response.json()[0]['category'] == "TI"
```

### Test Naming

- Test classes: `Test<ModelName>` or `Test<Feature>`
- Test methods: `test_<what_is_being_tested>`
- Use descriptive docstrings

### Pytest Fixtures

Leverage pytest fixtures for reusable test setup:

```python
import pytest
from app.factories import CountryFactory, StateFactory

@pytest.fixture
def brazil():
    """Create Brazil country fixture."""
    return CountryFactory(name="Brazil", code="BR")

@pytest.fixture
def sao_paulo(brazil):
    """Create São Paulo state fixture."""
    return StateFactory(name="São Paulo", code="SP", country=brazil)

def test_state_belongs_to_country(sao_paulo, brazil):
    """Test that state correctly references its country."""
    assert sao_paulo.country == brazil
```

## Database Conventions

### Query Optimization

#### Use select_related for Foreign Keys

```python
# ✅ Good - Single query
lands = Land.objects.select_related(
    'municipality__state__country',
    'biome'
)

# ❌ Bad - N+1 queries
lands = Land.objects.all()
for land in lands:
    print(land.municipality.state.country.name)  # Multiple queries!
```

#### Use prefetch_related for Reverse Relationships

```python
# ✅ Good - Two queries total
communities = Community.objects.prefetch_related('lands')

# ❌ Bad - N+1 queries
communities = Community.objects.all()
for community in communities:
    print(community.lands.count())  # Query per community!
```

### Migrations

#### Migration Best Practices

1. **Review generated migrations** - Always check what Django generates
2. **Add helpful comments** - Document complex data migrations
3. **Test migrations** - Ensure they work on production-like data
4. **Keep migrations small** - One logical change per migration

#### Adding Fields to Existing Models

When adding a field to an existing model, make it nullable:

```python
# ✅ Good - Nullable field
new_field = models.CharField(max_length=100, null=True, blank=True)

# ❌ Bad - Non-nullable on existing model (requires default)
new_field = models.CharField(max_length=100)
```

## Code Organization

### App Structure

The `app/` directory follows this organization:

```
app/
├── __init__.py
├── admin.py              # Django admin configuration
├── apps.py               # App configuration
├── factories.py          # Factory-boy factories for testing
├── filters.py            # django-filter FilterSet classes
├── models.py             # Django models
├── serializers.py        # DRF serializers
├── urls.py               # URL routing
├── views.py              # API views (if not using viewsets)
├── viewsets.py           # DRF viewsets
├── management/
│   └── commands/         # Custom management commands
│       └── load_isa_data.py
├── migrations/           # Database migrations
└── tests/                # Test modules
    ├── __init__.py
    ├── test_api.py
    ├── test_commands.py
    └── test_views.py
```

### Import Organization

Follow this import order (enforced by isort):

```python
# 1. Standard library
import uuid
from datetime import datetime

# 2. Django imports
from django.db import models
from django.utils.text import slugify

# 3. Third-party libraries
from rest_framework import serializers
import factory

# 4. Local application imports
from app.models import Land, Country
```

## Admin Customization

### Admin Class Patterns

#### ✅ Customized Admin

```python
from django.contrib import admin
from django.utils.html import format_html
from .models import Land

@admin.register(Land)
class LandAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "municipality",
        "biome",
        "category",
        "communities_list",
        "source_name",
        "isa_link"
    )
    list_filter = ("biome", "category", "source_name")
    search_fields = ("name", "source_id")
    autocomplete_fields = ("communities",)
    ordering = ("name",)
    readonly_fields = (
        "source_id",
        "source_name",
        "source_updated_at",
        "source_last_synced_at",
        "source_raw_data",
    )

    def communities_list(self, obj):
        """Display comma-separated list of communities."""
        return ", ".join([c.name for c in obj.communities.all()])

    communities_list.short_description = "Communities"

    def isa_link(self, obj):
        """Generate external link to ISA database."""
        if not obj.source_id or obj.source_name != "ISA":
            return None
        isa_url = "https://terrasindigenas.org.br/en/terras-indigenas/"
        return format_html(
            "<a href='%s%s' target='_blank'>source link</a>" % (isa_url, obj.source_id)
        )

    isa_link.allow_tags = True
    isa_link.short_description = "External link"
```

### Admin Conventions

- Use `@admin.register()` decorator
- Add `list_display` for important fields
- Add `list_filter` for filterable fields
- Add `search_fields` for searchable text fields
- Use `autocomplete_fields` for many-to-many and foreign keys
- Use `readonly_fields` for system-managed fields
- Add custom methods for computed columns
- Use `format_html()` for safe HTML in admin

## Summary

These conventions ensure consistency across the Kapok backend codebase. When in doubt:

1. **Follow existing patterns** - Look for similar code in the project
2. **Prioritize readability** - Code is read more than written
3. **Write tests** - All new code should have tests
4. **Document complex logic** - Use docstrings and comments
5. **Use type hints** - Add type hints where they add clarity
6. **Optimize queries** - Use select_related and prefetch_related
7. **Keep it simple** - Don't over-engineer solutions

For questions about these conventions, check the existing codebase or consult with the team.
