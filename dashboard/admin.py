from django.contrib import admin
from .models import PartnershipInquiry, FounderProfile, CorporatePartner

@admin.register(PartnershipInquiry)
class PartnershipInquiryAdmin(admin.ModelAdmin):
    list_display = ('organization_name', 'contact_name', 'email', 'partnership_interests', 'created_at', 'is_reviewed')
    list_filter = ('is_reviewed', 'created_at')
    search_fields = ('organization_name', 'contact_name', 'email', 'message')
    ordering = ('-created_at',)

@admin.register(FounderProfile)
class FounderProfileAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'title', 'education', 'graduation_year', 'cgpa', 'updated_at')

@admin.register(CorporatePartner)
class CorporatePartnerAdmin(admin.ModelAdmin):
    list_display = ('company_name', 'tier', 'status', 'is_published', 'is_featured_home', 'chairman_name', 'contact_person_name', 'display_order', 'created_at')
    list_filter = ('tier', 'status', 'is_published', 'is_featured_home', 'created_at')
    search_fields = ('company_name', 'chairman_name', 'chairman_title', 'contact_person_name', 'contact_email')
    ordering = ('display_order', '-created_at')
    actions = ['approve_and_publish', 'mark_under_review']

    @admin.action(description="Approve & Publish Selected Partners")
    def approve_and_publish(self, request, queryset):
        queryset.update(status='APPROVED', is_published=True)

    @admin.action(description="Mark Selected Partners as Under Review")
    def mark_under_review(self, request, queryset):
        queryset.update(status='UNDER_REVIEW')

