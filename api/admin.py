from django.contrib import admin
from .models import User, Boat, FisherfolkBoat, Fisherfolk, BirukbilugTracker, BoatBirukbilugTracker, MunicipalAgriculturist, ProvincialAgriculturist
from .forms import UserCreationForm, UserChangeForm
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

class UserAdmin(BaseUserAdmin):
    add_form = UserCreationForm
    form = UserChangeForm
    model = User
    list_display = ('username', 'email', 'user_role', 'is_staff', 'is_active')
    list_filter = ('user_role', 'is_staff', 'is_active')
    fieldsets = (
        (None, {'fields': ('username', 'email', 'password')}),
        ('Permissions', {'fields': ('user_role', 'is_staff', 'is_active', 'is_superuser', 'groups', 'user_permissions')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'user_role', 'password1', 'password2', 'is_staff', 'is_active')}
        ),
    )
    search_fields = ('username', 'email')
    ordering = ('username',)

@admin.register(Boat)
class BoatAdmin(admin.ModelAdmin):
    list_display = ('boat_id', 'boat_name', 'boat_type', 'material_used')
    list_filter = ('boat_type', 'material_used')
    search_fields = ('boat_id', 'boat_name')
    ordering = ('-date_added',)

@admin.register(FisherfolkBoat)
class FisherfolkBoatAdmin(admin.ModelAdmin):
    list_display = ('boat_registry_no', 'fisherfolk_number', 'boat_id', 'type_of_ownership')
    search_fields = ('boat_registry_no', 'fisherfolk_number__fisherfolk_number', 'boat_id__boat_name')
    ordering = ('-date_added',)

@admin.register(Fisherfolk)
class FisherfolkAdmin(admin.ModelAdmin):
    list_display = ('fisherfolk_number', 'registration_number', 'last_name', 'first_name', 'municipality')
    list_filter = ('municipality', 'fishery_section')
    search_fields = ('fisherfolk_number', 'registration_number', 'last_name', 'first_name')
    ordering = ('-date_added',)

@admin.register(BirukbilugTracker)
class BirukbilugTrackerAdmin(admin.ModelAdmin):
    list_display = ('BirukBilugID', 'municipality', 'status', 'date_added')
    list_filter = ('municipality', 'status')
    search_fields = ('BirukBilugID', 'municipality')
    ordering = ('-date_added',)

@admin.register(BoatBirukbilugTracker)
class BoatBirukbilugTrackerAdmin(admin.ModelAdmin):
    list_display = ('TrackingNo', 'BirukBilugID', 'BoatRegistryNo', 'Timestamp', 'Longitude', 'Latitude')
    list_filter = ('BirukBilugID', 'BoatRegistryNo', 'Timestamp')
    search_fields = ('TrackingNo', 'BirukBilugID__BirukBilugID', 'BoatRegistryNo__BoatRegistryNo')
    ordering = ('-Timestamp',)

@admin.register(MunicipalAgriculturist)
class MunicipalAgriculturistAdmin(admin.ModelAdmin):
    list_display = ('municipal_agriculturist_id', 'first_name', 'last_name', 'municipality', 'position', 'status')
    list_filter = ('municipality', 'position', 'status')
    search_fields = ('first_name', 'last_name', 'municipality')
    ordering = ('-date_added',)

@admin.register(ProvincialAgriculturist)
class ProvincialAgriculturistAdmin(admin.ModelAdmin):
    list_display = ('provincial_agriculturist_id', 'first_name', 'last_name', 'position', 'status')
    list_filter = ('position', 'status')
    search_fields = ('first_name', 'last_name')
    ordering = ('-date_added',)

admin.site.register(User, UserAdmin)
