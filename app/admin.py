from django.contrib import admin
from django.utils.html import format_html

from .models import Biome, Community, Country, IndigenousUser, Land, Municipality, State


@admin.register(Country)
class CountryAdmin(admin.ModelAdmin):
    list_display = ("name", "code")
    ordering = ("name",)


@admin.register(State)
class StateAdmin(admin.ModelAdmin):
    list_display = ("name", "name_local", "code", "country")
    list_filter = ("country",)
    ordering = ("name",)


@admin.register(Municipality)
class MunicipalityAdmin(admin.ModelAdmin):
    list_display = ("name", "name_local", "code", "state")
    list_filter = ("state",)
    search_fields = ("name", "code")
    ordering = ("name",)


@admin.register(Biome)
class BiomeAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "name_local",
        "country",
        "lands_count",
    )
    list_filter = ("country",)
    ordering = ("name",)

    @admin.display(description="Lands Count")
    def lands_count(self, obj):
        return obj.lands.count()


@admin.register(Land)
class LandAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "municipality",
        "biome",
        "category",
        "communities_list",
        "source_name",
        "isa_link",
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

    @admin.display(description="Communities")
    def communities_list(self, obj):
        """Display comma-separated list of communities"""
        return ", ".join([c.name for c in obj.communities.all()])

    @admin.display(description="External link")
    def isa_link(self, obj):
        if not obj.source_id or obj.source_name != "ISA":
            return None
        isa_url = "https://terrasindigenas.org.br/en/terras-indigenas/"
        return format_html(f"<a href='{isa_url}{obj.source_id}' target='_blank'>source link</a>")


@admin.register(Community)
class CommunityAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "lands_count")
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}
    ordering = ("name",)

    @admin.display(description="Lands Count")
    def lands_count(self, obj):
        return obj.lands.count()


@admin.register(IndigenousUser)
class IndigenousUserAdmin(admin.ModelAdmin):
    list_display = (
        "full_name",
        "username",
        "email",
        "land",
        "verification_tier",
        "created_at",
    )
    list_filter = ("verification_tier", "land__category")
    search_fields = ("full_name", "user__username", "user__email", "phone")
    readonly_fields = ("created_at", "updated_at")
    autocomplete_fields = ("land",)
    ordering = ("-created_at",)

    fieldsets = (
        ("User Account", {"fields": ("user",)}),
        ("Profile Information", {"fields": ("full_name", "phone", "land")}),
        ("Verification", {"fields": ("verification_tier",)}),
        ("Metadata", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )

    @admin.display(description="Username")
    def username(self, obj):
        return obj.user.username

    @admin.display(description="Email")
    def email(self, obj):
        return obj.user.email
