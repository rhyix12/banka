from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.core.exceptions import ValidationError
from django.utils.timezone import now
import random
from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import F
from PIL import Image
from io import BytesIO
from django.core.files.base import ContentFile
import os

# USER MANAGER
class UserManager(BaseUserManager):
    def create_user(self, username, email, password=None, **extra_fields):
        if not email:
            raise ValueError("The Email field must be set")
        email = self.normalize_email(email)
        user = self.model(username=username, email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('user_role', 'admin')

        if extra_fields.get('is_staff') is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get('is_superuser') is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self.create_user(username, email, password, **extra_fields)

# Municipal Agriculturist Model
class MunicipalAgriculturist(models.Model):
    municipal_agriculturist_id = models.AutoField(primary_key=True)
    first_name = models.CharField(max_length=100)
    middle_name = models.CharField(max_length=100, blank=True, null=True)
    last_name = models.CharField(max_length=100)
    sex = models.CharField(max_length=10)
    municipality = models.CharField(max_length=100)
    contact_number = models.CharField(max_length=20)
    position = models.CharField(max_length=100)
    status = models.CharField(max_length=20)
    date_added = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

# Provincial Agriculturist Model
class ProvincialAgriculturist(models.Model):
    provincial_agriculturist_id = models.AutoField(primary_key=True)
    first_name = models.CharField(max_length=100)
    middle_name = models.CharField(max_length=100, blank=True, null=True)
    last_name = models.CharField(max_length=100)
    sex = models.CharField(max_length=10)
    contact_number = models.CharField(max_length=20)
    position = models.CharField(max_length=100)
    status = models.CharField(max_length=20)
    date_added = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

# USER MODEL
class User(AbstractBaseUser, PermissionsMixin):
    USER_ROLES = (
        ('admin', 'Admin'),
        ('provincial_agriculturist', 'Provincial Agriculturist'),
        ('municipal_agriculturist', 'Municipal Agriculturist'),
    )

    GENDER_CHOICES = (
        ('male', 'Male'),
        ('female', 'Female'),
    )

    id = models.AutoField(primary_key=True)
    municipal_agriculturist = models.ForeignKey(MunicipalAgriculturist, on_delete=models.SET_NULL, null=True, blank=True)
    provincial_agriculturist = models.ForeignKey(ProvincialAgriculturist, on_delete=models.SET_NULL, null=True, blank=True)
    username = models.CharField(
        max_length=100, 
        unique=True,
        error_messages={
            'unique': 'A user with this username already exists.',
        }
    )
    password = models.CharField(max_length=128)
    email = models.EmailField(
        unique=True,
        error_messages={
            'unique': 'A user with this email address already exists.',
        }
    )
    sex = models.CharField(max_length=10, choices=GENDER_CHOICES, null=True, blank=True)
    last_login = models.DateTimeField(null=True, blank=True)
    is_superuser = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)
    user_role = models.CharField(max_length=30, choices=USER_ROLES)
    is_active = models.BooleanField(default=True)
    date_added = models.DateTimeField(auto_now_add=True)

    objects = UserManager()

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['email', 'user_role']

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['username'],
                name='unique_username_case_insensitive',
                condition=models.Q(is_active=True)
            ),
            models.UniqueConstraint(
                fields=['email'],
                name='unique_email_case_insensitive',
                condition=models.Q(is_active=True)
            )
        ]

    def clean(self):
        super().clean()
        # Convert username and email to lowercase before saving
        if self.username:
            self.username = self.username.lower()
        if self.email:
            self.email = self.email.lower()

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.username

class Fisherfolk(models.Model):
    id = models.AutoField(primary_key=True)
    fisherfolk_number = models.CharField(max_length=50, unique=True)
    registration_number = models.CharField(max_length=50, unique=True, blank=True)
    last_name = models.CharField(max_length=100)
    first_name = models.CharField(max_length=100)
    middle_name = models.CharField(max_length=100, blank=True, null=True)
    appelation = models.CharField(max_length=20, blank=True, null=True)
    civil_status = models.CharField(max_length=20)
    nationality = models.CharField(max_length=100)
    barangay = models.CharField(max_length=100)
    municipality = models.CharField(max_length=100)
    schedule = models.CharField(max_length=100, choices=[('Part Time', 'Part Time'), ('Full Time', 'Full Time')])
    contact_number = models.CharField(max_length=20)
    birth_date = models.DateField()
    birth_place = models.CharField(max_length=200)
    sex = models.CharField(max_length=10, choices=[('Male', 'Male'), ('Female', 'Female')])
    fishery_section = models.CharField(max_length=100)
    fishing_ground = models.CharField(max_length=100, blank=True, null=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='created_fisherfolk'
    )
    
    picture = models.ImageField(upload_to='fisherfolk_pictures/', blank=True, null=True)

    date_added = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['first_name', 'middle_name', 'last_name', 'birth_date'],
                name='unique_fisherfolk_identity'
            )
        ]

    def clean(self):
        super().clean()
        # Convert names to title case for consistency
        if self.first_name:
            self.first_name = self.first_name.strip().title()
        if self.middle_name:
            self.middle_name = self.middle_name.strip().title()
        if self.last_name:
            self.last_name = self.last_name.strip().title()

        # Check for existing fisherfolk with same details
        existing_query = Fisherfolk.objects.filter(
            first_name__iexact=self.first_name,
            last_name__iexact=self.last_name,
            birth_date=self.birth_date
        )
        
        if self.middle_name:
            existing_query = existing_query.filter(middle_name__iexact=self.middle_name)
        else:
            existing_query = existing_query.filter(middle_name__isnull=True)

        if self.pk:  # If this is an update
            existing_query = existing_query.exclude(pk=self.pk)

        if existing_query.exists():
            raise ValidationError('A fisherfolk with these details already exists.')

    def save(self, *args, **kwargs):
        if not self.fisherfolk_number:
            last = Fisherfolk.objects.order_by('-id').first()
            next_number = 1 if not last else last.id + 1
            self.fisherfolk_number = f"FF-{next_number:06d}"  # Example: FF-000001
        self.full_clean()
        super().save(*args, **kwargs)

    def resize_image(self, image_field):
        if not image_field:
            return

        # Open the uploaded image
        img = Image.open(image_field)

        # Convert to RGB if necessary
        if img.mode != 'RGB':
            img = img.convert('RGB')

        # Calculate target size (2x2 inches at 300 DPI)
        target_size = (600, 600)  # 2 inches * 300 DPI = 600 pixels

        # Resize image maintaining aspect ratio
        img.thumbnail((600, 600), Image.Resampling.LANCZOS)

        # Create a new white background image
        new_img = Image.new('RGB', target_size, 'white')

        # Calculate position to paste the resized image (center it)
        x = (target_size[0] - img.size[0]) // 2
        y = (target_size[1] - img.size[1]) // 2

        # Paste the resized image onto the white background
        new_img.paste(img, (x, y))

        # Save the processed image
        buffer = BytesIO()
        new_img.save(buffer, format='JPEG', quality=90)
        buffer.seek(0)

        # Generate a new filename
        original_name = os.path.splitext(image_field.name)[0]
        new_name = f"{original_name}_2x2.jpg"

        # Save the new image
        image_field.save(
            new_name,
            ContentFile(buffer.read()),
            save=False
        )

    def __str__(self):
        return f"{self.fisherfolk_number} - {self.last_name}, {self.first_name}"

class Boat(models.Model):
    boat_id = models.AutoField(primary_key=True)
    boat_name = models.CharField(max_length=100, blank=True, null=True)
    boat_type = models.CharField(max_length=50)
    built_place = models.CharField(max_length=100)
    built_year = models.IntegerField()
    material_used = models.CharField(max_length=100)
    registered_length = models.DecimalField(max_digits=10, decimal_places=2)
    registered_breadth = models.DecimalField(max_digits=10, decimal_places=2)
    registered_depth = models.DecimalField(max_digits=10, decimal_places=2)
    boat_image = models.ImageField(upload_to='boat_images/', blank=True, null=True)
    is_active = models.BooleanField(default=True)
    date_added = models.DateTimeField(auto_now_add=True)

    def clean(self):
        super().clean()
        # If boat_name is blank or None, set to "Unnamed"
        if not self.boat_name or self.boat_name.strip() == "":
            self.boat_name = "Unnamed"
        else:
            self.boat_name = self.boat_name.strip().title()
        # Only enforce uniqueness if not "Unnamed"
        if self.boat_name != "Unnamed":
            existing_query = Boat.objects.filter(boat_name__iexact=self.boat_name)
            if self.pk:
                existing_query = existing_query.exclude(pk=self.pk)
            if existing_query.exists():
                raise ValidationError('A boat with this name already exists.')

    def save(self, *args, **kwargs):
        self.full_clean()  # This will call clean() and validate all fields
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.boat_name}"

class BirukbilugTracker(models.Model):
    BirukBilugID = models.AutoField(primary_key=True)
    municipality = models.CharField(max_length=100)
    status = models.CharField(max_length=20)
    date_added = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Tracker {self.BirukBilugID} - {self.municipality}"
    
class FisherfolkBoat(models.Model):
    boat_registry_no = models.AutoField(primary_key=True)
    fisherfolk_number = models.ForeignKey(Fisherfolk, on_delete=models.CASCADE)
    boat_id = models.ForeignKey(Boat, on_delete=models.CASCADE)
    
    type_of_ownership = models.CharField(max_length=50)
    
    no_of_fishers = models.IntegerField()
    homeport = models.CharField(max_length=100)
    date_added = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    BirukBilugID = models.ForeignKey(BirukbilugTracker, on_delete=models.CASCADE, unique=True, null=True)

    def __str__(self):
        return f"{self.boat_registry_no} - {self.fisherfolk_number.fisherfolk_number}"

    def save(self, *args, **kwargs):
        self.is_active = True  
        super().save(*args, **kwargs)

class BoatBirukbilugTracker(models.Model):
    TrackingNo = models.AutoField(primary_key=True)
    BirukBilugID = models.ForeignKey(BirukbilugTracker, on_delete=models.CASCADE)
    BoatRegistryNo = models.ForeignKey(FisherfolkBoat, on_delete=models.CASCADE)
    Timestamp = models.DateTimeField(auto_now_add=True)
    Longitude = models.DecimalField(max_digits=9, decimal_places=6)
    Latitude = models.DecimalField(max_digits=9, decimal_places=6)

    def __str__(self):
        return f"Tracking {self.TrackingNo} - Boat {self.BoatRegistryNo.BoatRegistryNo}"

class ActivityLog(models.Model):
    logId = models.AutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    action = models.CharField(max_length=255)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.action} at {self.timestamp}"



class GPSData(models.Model):    
    latitude = models.FloatField()
    longitude = models.FloatField()
    boat_id = models.IntegerField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Boat {self.boat_id} @ {self.latitude},{self.longitude}"


