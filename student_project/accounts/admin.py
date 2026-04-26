from django.contrib import admin
from accounts.models import User

# EDUCATIONAL FEATURE: ModelAdmin allows fine-grained customization of how 
# a Django model shows up in the built-in admin panel (/admin).

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    # list_display controls which fields are visible in the table structure
    list_display = ("username", "email", "role", "is_active", "date_joined")
    
    # list_filter adds a sidebar filtering UI
    list_filter = ("role", "is_active", "is_staff", "is_superuser")
    
    # search_fields adds a search bar that performs ILIKE queries on these fields
    search_fields = ("username", "email")
    
    # readonly_fields protects critical timestamp fields from being manually edited
    readonly_fields = ("last_login_time", "date_joined")
