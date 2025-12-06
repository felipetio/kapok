"""Factory classes for creating test data using factory-boy."""

from django.contrib.auth.models import User

import factory
from factory.django import DjangoModelFactory

from app.models import (
    Biome,
    Community,
    Country,
    IndigenousUser,
    Land,
    Membership,
    Municipality,
    Organization,
    State,
    Vouching,
    VouchingConfig,
)


class CountryFactory(DjangoModelFactory):
    """Factory for creating Country instances."""

    class Meta:
        model = Country

    name = factory.Faker("country")
    code = factory.Faker("country_code")


class StateFactory(DjangoModelFactory):
    """Factory for creating State instances."""

    class Meta:
        model = State

    name = factory.Faker("state")
    code = factory.Faker("state_abbr")
    name_local = factory.Faker("state")
    country = factory.SubFactory(CountryFactory)


class MunicipalityFactory(DjangoModelFactory):
    """Factory for creating Municipality instances."""

    class Meta:
        model = Municipality

    name = factory.Faker("city")
    name_local = factory.Faker("city")
    state = factory.SubFactory(StateFactory)


class BiomeFactory(DjangoModelFactory):
    """Factory for creating Biome instances."""

    class Meta:
        model = Biome

    name = factory.Faker("word")
    name_local = factory.Faker("word")
    description = factory.Faker("text", max_nb_chars=200)
    description_local = factory.Faker("text", max_nb_chars=200)
    country = factory.SubFactory(CountryFactory)


class CommunityFactory(DjangoModelFactory):
    """Factory for creating Community instances."""

    class Meta:
        model = Community

    name = factory.Faker("company")
    slug = factory.Faker("slug")


class LandFactory(DjangoModelFactory):
    """Factory for creating Land instances."""

    class Meta:
        model = Land

    name = factory.Faker("city")
    category = factory.Iterator(["TI", "RI", "PI", "DI"])
    municipality = factory.SubFactory(MunicipalityFactory)
    biome = factory.SubFactory(BiomeFactory)

    @factory.post_generation
    def communities(self, create, extracted, **kwargs):
        """Handle many-to-many relationship for communities."""
        if not create:
            return

        if extracted:
            for community in extracted:
                self.communities.add(community)


class UserFactory(DjangoModelFactory):
    """Factory for creating User instances."""

    class Meta:
        model = User

    username = factory.Faker("user_name")
    email = factory.Faker("email")
    password = factory.PostGenerationMethodCall("set_password", "testpass123")


class IndigenousUserFactory(DjangoModelFactory):
    """Factory for creating IndigenousUser instances."""

    class Meta:
        model = IndigenousUser

    user = factory.SubFactory(UserFactory)
    land = factory.SubFactory(LandFactory)
    full_name = factory.Faker("name")
    phone = factory.Sequence(lambda n: f"+55{n:011d}"[:20])  # Max 20 chars
    verification_tier = "PENDING"


class VouchingConfigFactory(DjangoModelFactory):
    """Factory for creating VouchingConfig instances."""

    class Meta:
        model = VouchingConfig

    land = factory.SubFactory(LandFactory)
    min_validators = 2
    rejection_cooldown_days = 30
    vouching_request_expiry_days = 30


class VouchingFactory(DjangoModelFactory):
    """Factory for creating Vouching instances."""

    class Meta:
        model = Vouching

    requester = factory.SubFactory(IndigenousUserFactory, verification_tier="PENDING")
    validator = factory.SubFactory(IndigenousUserFactory, verification_tier="VERIFIED")
    status = "PENDING"
    message = factory.Faker("sentence")


class OrganizationFactory(DjangoModelFactory):
    """Factory for creating Organization instances."""

    class Meta:
        model = Organization

    name = factory.Faker("company")
    slug = factory.Faker("slug")
    type = factory.Iterator(["ASSOCIATION", "FEDERATION", "COOPERATIVE", "OTHER"])
    status = "ACTIVE"
    description = factory.Faker("text", max_nb_chars=200)
    website = factory.Faker("url")
    email = factory.Faker("email")
    phone = factory.Sequence(lambda n: f"+55{n:011d}"[:20])
    registration_number = factory.Faker("uuid4")
    created_by = factory.SubFactory(IndigenousUserFactory, verification_tier="VERIFIED")

    @factory.post_generation
    def lands(self, create, extracted, **kwargs):
        """Handle many-to-many relationship for lands."""
        if not create:
            return

        if extracted:
            for land in extracted:
                self.lands.add(land)


class MembershipFactory(DjangoModelFactory):
    """Factory for creating Membership instances."""

    class Meta:
        model = Membership

    organization = factory.SubFactory(OrganizationFactory)
    user = factory.SubFactory(IndigenousUserFactory, verification_tier="VERIFIED")
    role = "MEMBER"
