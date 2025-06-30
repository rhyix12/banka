from rest_framework import serializers
from .models import GPSData, User, Boat, BoatBirukbilugTracker, Fisherfolk, BirukbilugTracker, FisherfolkBoat, MunicipalAgriculturist, ProvincialAgriculturist, ActivityLog
import re
from datetime import date
from django.utils import timezone
from django.db.models.signals import post_save
from django.dispatch import receiver
from PIL import Image


@receiver(post_save, sender=Fisherfolk)
def log_fisherfolk_created(sender, instance, created, **kwargs):
    if created:
        ActivityLog.objects.create(
            user=instance.created_by,  # or another user reference
            action=f"Fisherfolk {instance} was created",
        )
        
class MunicipalAgriculturistSerializer(serializers.ModelSerializer):
    class Meta:
        model = MunicipalAgriculturist
        fields = ['municipal_agriculturist_id','first_name', 'middle_name', 'last_name', 'sex', 'municipality', 'contact_number', 'position']

class ProvincialAgriculturistSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProvincialAgriculturist
        fields = ['provincial_agriculturist_id','first_name', 'middle_name', 'last_name', 'sex', 'contact_number', 'position']

class UserSerializer(serializers.ModelSerializer):
    municipal_agriculturist = MunicipalAgriculturistSerializer(read_only=True)
    provincial_agriculturist = ProvincialAgriculturistSerializer(read_only=True)
    
    # Fields for creating/updating agriculturist
    first_name = serializers.CharField(write_only=True)
    middle_name = serializers.CharField(write_only=True, required=False, allow_blank=True)
    last_name = serializers.CharField(write_only=True)
    sex = serializers.CharField(write_only=True)
    contact_number = serializers.CharField(write_only=True)
    position = serializers.CharField(write_only=True)
    municipality = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'password', 'user_role', 'is_active',
            'municipal_agriculturist', 'provincial_agriculturist',
            'first_name', 'middle_name', 'last_name', 'sex', 
            'contact_number', 'position', 'municipality'
        ]
        extra_kwargs = {
            'password': {'write_only': True},
            'username': {
                'error_messages': {
                    'unique': 'A user with this username already exists.',
                    'invalid': 'Username can only contain letters, numbers, and underscores.',
                }
            },
            'email': {
                'error_messages': {
                    'unique': 'A user with this email address already exists.',
                    'invalid': 'Enter a valid email address.',
                }
            }
        }

    def validate(self, data):
        # Check if trying to deactivate an admin user
        if 'is_active' in data and not data['is_active']:
            if self.instance and self.instance.user_role == 'admin':
                raise serializers.ValidationError({
                    "is_active": "Admin accounts cannot be deactivated"
                })

        # Require municipality only for municipal agriculturists
        user_role = data.get('user_role')
        if not user_role and self.instance:
            user_role = self.instance.user_role

        if user_role == 'municipal_agriculturist':
            municipality = data.get('municipality')
            if not municipality:
                raise serializers.ValidationError({'municipality': 'This field is required for Municipal Agriculturists.'})
        
        # Validate username and email uniqueness case-insensitively
        username = data.get('username', '').lower()
        email = data.get('email', '').lower()

        # Username uniqueness check
        username_exists = User.objects.filter(username__iexact=username)
        if self.instance:
            username_exists = username_exists.exclude(pk=self.instance.pk)
        if username_exists.exists():
            raise serializers.ValidationError({
                'username': 'A user with this username already exists.'
            })

        # Email uniqueness check
        email_exists = User.objects.filter(email__iexact=email)
        if self.instance:
            email_exists = email_exists.exclude(pk=self.instance.pk)
        if email_exists.exists():
            raise serializers.ValidationError({
                'email': 'A user with this email address already exists.'
            })

        # Convert username and email to lowercase
        if 'username' in data:
            data['username'] = username
        if 'email' in data:
            data['email'] = email
        
        return data

    def validate_user_role(self, value):
        value = value.strip().lower()  
        if value not in dict(User.USER_ROLES).keys():
            raise serializers.ValidationError("Invalid user role")
        return value

    def validate_contact_number(self, value):
        if value:
            # Handle both formats: 09XXXXXXXXX or +639XXXXXXXXX
            if value.startswith('+63'):
                # Remove +63 prefix and validate remaining number
                number = value[3:]  # Skip +63
                if not number.startswith('9') or len(number) != 10:
                    raise serializers.ValidationError(
                        "Phone number must be in format 09XXXXXXXXX or +639XXXXXXXXX"
                    )
            elif value.startswith('09'):
                # Already in 09XXXXXXXXX format
                if len(value) != 11:
                    raise serializers.ValidationError(
                        "Phone number must be in format 09XXXXXXXXX or +639XXXXXXXXX"
                    )
            else:
                raise serializers.ValidationError(
                    "Phone number must be in format 09XXXXXXXXX or +639XXXXXXXXX"
                )
            
            # Standardize format to +63 format
            if value.startswith('0'):
                return f"+63{value[1:]}"  # Convert 09... to +639...
            return value  # Already in +63 format
        return value

    def validate_sex(self, value):
        if value:
            value = value.lower()
            if value not in dict(User.GENDER_CHOICES).keys():
                raise serializers.ValidationError("Sex must be either 'male' or 'female'")
        return value

    def validate_username(self, value):
        if not value:
            raise serializers.ValidationError("Username is required.")
        
        # Convert to lowercase for validation
        value = value.lower()
        
        # Check for valid characters (letters, numbers, underscores)
        if not re.match(r'^[a-z0-9_]+$', value):
            raise serializers.ValidationError(
                "Username can only contain lowercase letters, numbers, and underscores."
            )
        
        return value

    def validate_email(self, value):
        if not value:
            raise serializers.ValidationError("Email is required.")
        
        # Convert to lowercase for validation
        value = value.lower()
        
        # Basic email format validation
        if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', value):
            raise serializers.ValidationError("Enter a valid email address.")
        
        return value

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['user_role'] = instance.user_role.strip().lower()
        if instance.sex:
            representation['sex'] = instance.sex.lower()
        if instance.municipal_agriculturist:
            representation['municipality'] = instance.municipal_agriculturist.municipality
        return representation

    def create(self, validated_data):
        # Extract agriculturist data
        agriculturist_data = {
            'first_name': validated_data.pop('first_name'),
            'middle_name': validated_data.pop('middle_name', ''),
            'last_name': validated_data.pop('last_name'),
            'sex': validated_data.pop('sex'),
            'contact_number': validated_data.pop('contact_number'),
            'position': validated_data.pop('position'),
            'status': 'Active' if validated_data.get('is_active', True) else 'Inactive',
        }

        # Municipality may or may not be present in validated_data
        municipality_name = validated_data.pop('municipality', None)

        user_role = validated_data.get('user_role')

        # Create agriculturist record
        if user_role == 'municipal_agriculturist':
            agriculturist_data['municipality'] = municipality_name
            agriculturist = MunicipalAgriculturist.objects.create(**agriculturist_data)
            validated_data['municipal_agriculturist'] = agriculturist
        else:
            agriculturist = ProvincialAgriculturist.objects.create(**agriculturist_data)
            validated_data['provincial_agriculturist'] = agriculturist

        # Create user
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        
        return user

    def update(self, instance, validated_data):
        # Extract agriculturist data if provided
        agriculturist_data = {}
        agriculturist_fields = ['first_name', 'middle_name', 'last_name', 'sex', 'contact_number', 'position', 'municipality']
        
        for field in agriculturist_fields:
            if field in validated_data:
                # Convert field name to match agriculturist model
                ag_field = {
                    'first_name': 'first_name',
                    'middle_name': 'middle_name',
                    'last_name': 'last_name',
                    'sex': 'sex',
                    'contact_number': 'contact_number',
                    'position': 'position',
                    'municipality': 'municipality'
                }[field]
                agriculturist_data[ag_field] = validated_data.pop(field)

        # Update agriculturist if data provided
        if agriculturist_data:
            if instance.user_role == 'municipal_agriculturist' and instance.municipal_agriculturist:
                for key, value in agriculturist_data.items():
                    setattr(instance.municipal_agriculturist, key, value)
                instance.municipal_agriculturist.save()
            elif instance.user_role == 'provincial_agriculturist' and instance.provincial_agriculturist:
                for key, value in agriculturist_data.items():
                    if key != 'municipality':  # Skip municipality for provincial
                        setattr(instance.provincial_agriculturist, key, value)
                instance.provincial_agriculturist.save()

        # Update password if provided
        if 'password' in validated_data:
            password = validated_data.pop('password')
            instance.set_password(password)

        # Update remaining user fields
        for key, value in validated_data.items():
            setattr(instance, key, value)
        
        instance.save()
        return instance

class BoatBirukbilugTrackerSerializer(serializers.ModelSerializer):
    class Meta:
        model = BoatBirukbilugTracker
        fields = ['TrackingNo', 'BirukBilugID', 'BoatRegistryNo', 'Timestamp', 'Longitude', 'Latitude']

class BirukbilugTrackerSerializer(serializers.ModelSerializer):
    class Meta:
        model = BirukbilugTracker
        fields = ['BirukBilugID', 'municipality', 'status', 'date_added']

class FisherfolkBoatSerializer(serializers.ModelSerializer):
    class Meta:
        model = FisherfolkBoat
        fields = ['boat_registry_no', 'fisherfolk_number', 'boat_id', 'type_of_ownership', 
                 'no_of_fishers', 'homeport', 'date_added', 'is_active', 'BirukBilugID']
    
    def validate_is_active(self, value):
        # Accept both boolean and string "true"/"false"
        if isinstance(value, str):
            return value.lower() == "true"
        return bool(value)

class BoatSerializer(serializers.ModelSerializer):
    location_history = BoatBirukbilugTrackerSerializer(many=True, read_only=True, source='fisherfolkboat_set.boatbirukbilugtracker_set')
    boat_image = serializers.ImageField(required=False)
    
    class Meta:
        model = Boat
        fields = '__all__'
        read_only_fields = ['boat_id', 'date_added']
    
    def validate_boat_name(self, value):
        if value is None or value.strip() == "":
            return "Unnamed"
        if value.lower() == "unnamed":
            return "Unnamed"
        # Check for uniqueness except for "Unnamed"
        if Boat.objects.filter(boat_name__iexact=value).exists():
            raise serializers.ValidationError("Boat name must be unique.")
        return value
    
    def validate(self, data):
        boat_name = data.get('boat_name', '').strip().title() if data.get('boat_name') else "Unnamed"
        # Only enforce uniqueness if not "Unnamed"
        if boat_name != "Unnamed":
            existing_query = Boat.objects.filter(boat_name__iexact=boat_name)
            if self.instance:
                existing_query = existing_query.exclude(pk=self.instance.pk)
            if existing_query.exists():
                raise serializers.ValidationError({
                    'non_field_errors': [
                        'A boat with this name already exists.'
                    ]
                })
        # Set boat_name to "Unnamed" if blank or None
        data['boat_name'] = boat_name    
        # If this is an update operation
        if self.instance is not None:
            # For updates, we don't need to validate boat_id
            if 'boat_id' in data:
                data.pop('boat_id')  # Remove boat_id from update data
        
        return data

class BoatLocationUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = BoatBirukbilugTracker
        fields = ['Longitude', 'Latitude', 'Timestamp']
        
    def update(self, instance, validated_data):
        # Get or create a BirukbilugTracker for the municipality
        birukbilug_tracker, _ = BirukbilugTracker.objects.get_or_create(
            Municipality=instance.municipality,
            defaults={'Status': 'active'}
        )
        
        # Get the FisherfolkBoat instance
        try:
            fisherfolk_boat = FisherfolkBoat.objects.get(BoatID=instance)
        except FisherfolkBoat.DoesNotExist:
            raise serializers.ValidationError("This boat is not registered to any fisherfolk")
        
        # Create a new location history entry
        BoatBirukbilugTracker.objects.create(
            BirukBilugID=birukbilug_tracker,
            BoatRegistryNo=fisherfolk_boat,
            Longitude=validated_data.get('Longitude'),
            Latitude=validated_data.get('Latitude'),
            Timestamp=validated_data.get('Timestamp')
        )
        
        return instance

class FisherfolkSerializer(serializers.ModelSerializer):
    picture = serializers.ImageField(required=False)
    signature = serializers.ImageField(required=False)

    class Meta:
        model = Fisherfolk
        fields = '__all__'
        read_only_fields = ['fisherfolk_number', 'date_added']

    def validate(self, data):
        # Check for existing fisherfolk with same name and birth date
        first_name = data.get('first_name', '').strip().title()
        middle_name = data.get('middle_name', '').strip().title() if data.get('middle_name') else None
        last_name = data.get('last_name', '').strip().title()
        birth_date = data.get('birth_date')

        # Skip validation if any of the required fields are missing
        if not all([first_name, last_name, birth_date]):
            return data

        # Build the query
        existing_query = Fisherfolk.objects.filter(
            first_name__iexact=first_name,
            last_name__iexact=last_name,
            birth_date=birth_date
        )

        # Add middle name to query if provided
        if middle_name:
            existing_query = existing_query.filter(middle_name__iexact=middle_name)
        else:
            existing_query = existing_query.filter(middle_name__isnull=True)

        # Exclude current instance in case of update
        if self.instance:
            existing_query = existing_query.exclude(pk=self.instance.pk)

        if existing_query.exists():
            existing = existing_query.first()
            raise serializers.ValidationError({
                'non_field_errors': [
                    f'A fisherfolk with these details already exists (Registration Number: {existing.registration_number})'
                ]
            })

        # Validate birth_date
        if birth_date:
            today = timezone.now().date()
            
            # Check if birth_date is in the future
            if birth_date > today:
                raise serializers.ValidationError({
                    'birth_date': 'Birth date cannot be in the future.'
                })
            
            # Calculate age
            age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
            
            # Check if person is at least 18 years old
            if age < 18:
                raise serializers.ValidationError({
                    'birth_date': 'Fisherfolk must be at least 18 years old.'
                })

        return data

    def validate_contact_number(self, value):
        if value:
            # Handle both formats: 09XXXXXXXXX or +639XXXXXXXXX
            if value.startswith('+63'):
                # Remove +63 prefix and validate remaining number
                number = value[3:]  # Skip +63
                if not number.startswith('9') or len(number) != 10:
                    raise serializers.ValidationError(
                        "Phone number must be in format 09XXXXXXXXX or +639XXXXXXXXX"
                    )
            elif value.startswith('09'):
                # Already in 09XXXXXXXXX format
                if len(value) != 11:
                    raise serializers.ValidationError(
                        "Phone number must be in format 09XXXXXXXXX or +639XXXXXXXXX"
                    )
            else:
                raise serializers.ValidationError(
                    "Phone number must be in format 09XXXXXXXXX or +639XXXXXXXXX"
                )
            
            # Standardize format to +63 format
            if value.startswith('0'):
                return f"+63{value[1:]}"  # Convert 09... to +639...
            return value
        return value

    def create(self, validated_data):
        try:
            # Handle image resizing before saving
            instance = super().create(validated_data)
            if instance.picture:
                instance.resize_image(instance.picture)

            # Generate fisherfolk number if not provided
            if not instance.fisherfolk_number:
                year = timezone.now().year
                last_id = Fisherfolk.objects.all().order_by('-fisherfolk_number').first()
                if last_id and f"{year}-" in last_id.fisherfolk_number:
                    last_serial = int(last_id.fisherfolk_number.split('-')[1])
                    new_serial = last_serial + 1
                else:
                    new_serial = 1
                instance.fisherfolk_number = f"{year}-{new_serial:05d}"

            instance.save()
            return instance
        except Exception as e:
            raise serializers.ValidationError(str(e))

    def to_representation(self, instance):
        data = super().to_representation(instance)
        # We explicitly set image URLs to None to avoid a crash if media URLs aren't configured.
        # This allows the list to load, although images won't be displayed.
        data['picture'] = None
        data['signature'] = None
        return data
    
class ActivityLogSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField(read_only=True)  # or use PrimaryKeyRelatedField if you want the ID

    class Meta:
        model = ActivityLog
        fields = ['logId', 'user', 'action', 'timestamp']
        read_only_fields = ['logId', 'user', 'timestamp']


class GPSDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = GPSData
        fields = ['latitude', 'longitude']