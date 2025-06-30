import json
from django.conf import settings
from django.http import JsonResponse
from rest_framework.response import Response
from rest_framework import status, viewsets, serializers
from rest_framework.decorators import api_view, permission_classes, action
from .models import GPSData,MunicipalAgriculturist, ProvincialAgriculturist, User, Boat, BoatBirukbilugTracker, Fisherfolk, BirukbilugTracker, FisherfolkBoat, ActivityLog, GPSData
from .serializers import BirukbilugTrackerSerializer, UserSerializer, BoatSerializer, BoatLocationUpdateSerializer, BoatBirukbilugTrackerSerializer, FisherfolkSerializer, FisherfolkBoatSerializer, ActivityLogSerializer, ProvincialAgriculturistSerializer, MunicipalAgriculturistSerializer
from rest_framework.permissions import AllowAny, IsAuthenticated
from .permissions import IsAdmin, IsSelfOrAdmin
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse


# TOKEN
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError, InvalidToken
from django.contrib.auth import authenticate, login
from django.contrib.auth.hashers import make_password
from django.db.models.functions import TruncMonth

#for generate report
from django.db.models import Q

from django.contrib.auth.models import AbstractUser, Group, Permission
from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone

# TOKEN
@api_view(['POST'])
@permission_classes([])
def login_view(request):
    try:
        username = request.data.get('username')
        password = request.data.get('password')

        if not username or not password:
            return Response({"message": "Username and password are required"}, status=status.HTTP_400_BAD_REQUEST)

        user = authenticate(request, username=username, password=password)
        
        if user is not None and user.is_active:
            login(request, user)
            refresh = RefreshToken.for_user(user)
            access_token = str(refresh.access_token)

            response = Response({
                "message": "Login successful",
                "access": access_token,
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "user_role": user.user_role,
                }
            }, status=status.HTTP_200_OK)

            # Set Access Token in Cookie
            response.set_cookie(
                key='access_token',
                value=access_token,
                httponly=True,
                samesite='Lax',
                secure=False,  # Set to True in production with HTTPS
                max_age=3600  # 1 hour
            )

            # Set Refresh Token in Cookie
            response.set_cookie(
                key='refresh_token',
                value=str(refresh),
                httponly=True,
                samesite='Lax',
                secure=False,  # Set to True in production with HTTPS
                max_age=86400  # 24 hours
            )

            return response
        else:
            return Response({"message": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)
            
    except Exception as e:
        print(f"Login error: {str(e)}")
        return Response({"message": "An error occurred during login"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([])
def logout_view(request):
    response = Response({'message': 'Logged out successfully'}, status=200)
    
    # Clear both cookies
    response.delete_cookie('access_token')
    response.delete_cookie('refresh_token')
    
    # Additional cookie clearing with explicit parameters
    response.set_cookie('access_token', '', expires=0, httponly=True, samesite='Lax', secure=False)
    response.set_cookie('refresh_token', '', expires=0, httponly=True, samesite='Lax', secure=False)

    return response

@api_view(['POST'])
@permission_classes([AllowAny])
def refresh_token_view(request):
    refresh_token = request.COOKIES.get('refresh_token')
    if not refresh_token:
        return Response({'error': 'No refresh token'}, status=401)

    try:
        cookie_secure = settings.SIMPLE_JWT.get("AUTH_COOKIE_SECURE", False)
        cookie_httponly = settings.SIMPLE_JWT.get("AUTH_COOKIE_HTTP_ONLY", True)
        cookie_samesite = settings.SIMPLE_JWT.get("AUTH_COOKIE_SAMESITE", "Lax")
        access_token_lifetime = int(settings.SIMPLE_JWT["ACCESS_TOKEN_LIFETIME"].total_seconds())

        refresh = RefreshToken(refresh_token)
        access = str(refresh.access_token)

        res = Response({'access': access}, status=200)
        res.set_cookie(
            'access_token',
            access,
            httponly=cookie_httponly,
            samesite=cookie_samesite,
            secure=cookie_secure,
            max_age=access_token_lifetime, 
            path="/"
        )

        return res
    except Exception:
        return Response({'detail': 'Invalid refresh token'}, status=403)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def protected_view(request):
    return Response({
        "authenticated": True,
        "user": {
            "id": request.user.id,
            "username": request.user.username,
            "user_role": request.user.user_role,
        }
    })


# USERS
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_users(request):
    role = request.query_params.get('role')
    if role:
        users = User.objects.filter(user_role=role)
    else:
        users = User.objects.all()
    serializer = UserSerializer(users, many=True)
    return Response(serializer.data)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_user(request):
    # Step 1 required fields (User Details)
    step1_fields = ['username', 'email', 'password', 'user_role']
    # Step 2 required fields (Personal Information)
    step2_fields = ['first_name', 'middle_name', 'last_name', 'sex', 'contact_number', 'position']

    # Add municipality to required fields if user_role is municipal_agriculturist
    if request.data.get('user_role') == 'municipal_agriculturist':
        step2_fields.append('municipality')

    required_fields = step1_fields + step2_fields
    missing_fields = [field for field in required_fields if not request.data.get(field) and field not in ['middle_name']]

    if missing_fields:
        return Response(
            {
                'error': 'The following fields are required:',
                'missing_fields': missing_fields,
                'step1_fields': step1_fields,
                'step2_fields': step2_fields
            },
            status=status.HTTP_400_BAD_REQUEST
        )

    # Flatten nested agriculturist object if provided
    if 'municipal_agriculturist' in request.data:
        agri = request.data.pop('municipal_agriculturist')
        if isinstance(agri, dict):
            request.data.update({
                'first_name': agri.get('first_name', agri.get('first_name')), 
                'middle_name': agri.get('middle_name', agri.get('middle_name', '')),
                'last_name': agri.get('last_name', agri.get('last_name')),
                'gender': agri.get('sex', agri.get('sex')),
                'contact_number': agri.get('contact_number', agri.get('contact_number')),
                'position': agri.get('position', agri.get('position')),
                'municipality': agri.get('municipality', agri.get('municipality')),
            })
    if 'provincial_agriculturist' in request.data:
        agri = request.data.pop('provincial_agriculturist')
        if isinstance(agri, dict):
            request.data.update({
                'first_name': agri.get('FirstName', agri.get('first_name')),
                'middle_name': agri.get('MiddleName', agri.get('middle_name', '')),
                'last_name': agri.get('LastName', agri.get('last_name')),
                'gender': agri.get('Sex', agri.get('gender')),
                'phone_number': agri.get('ContactNo', agri.get('phone_number')),
                'position': agri.get('Position', agri.get('position')),
            })

    # Prepare data for serializer
    data = request.data.copy()

    # Flatten nested agriculturist object if provided
    if 'municipal_agriculturist' in data:
        agri = data.pop('municipal_agriculturist')
        if isinstance(agri, dict):
            data.update({
                'first_name': agri.get('first_name') or agri.get('first_name'),
                'middle_name': agri.get('middle_name') or agri.get('middle_name', ''),
                'last_name': agri.get('last_name') or agri.get('last_name'),
                'sex': agri.get('sex') or agri.get('sex'),
                'contact_number': agri.get('contact_number') or agri.get('contact_number'),
                'position': agri.get('position') or agri.get('position'),
                'municipality': agri.get('municipality') or agri.get('municipality'),
            })
    if 'provincial_agriculturist' in data:
        agri = data.pop('provincial_agriculturist')
        if isinstance(agri, dict):
            data.update({
                'first_name': agri.get('FirstName') or agri.get('first_name'),
                'middle_name': agri.get('MiddleName') or agri.get('middle_name', ''),
                'last_name': agri.get('LastName') or agri.get('last_name'),
                'gender': agri.get('Sex') or agri.get('gender'),
                'phone_number': agri.get('ContactNo') or agri.get('phone_number'),
                'position': agri.get('Position') or agri.get('position'),
            })

    # Convert status string to boolean if provided as string
    if isinstance(data.get('is_active'), str):
        data['is_active'] = data['is_active'].lower() == 'true' or data['is_active'].lower() == 'active'

    serializer = UserSerializer(data=data)
    if serializer.is_valid():
        user = serializer.save()
        return Response(
            {
                'message': 'User created successfully',
                'user': UserSerializer(user).data
            },
            status=status.HTTP_201_CREATED
        )
    else:
        return Response(
            {
                'error': 'Invalid data.',
                'details': serializer.errors
            },
            status=status.HTTP_400_BAD_REQUEST
        )

@api_view(['GET', 'PUT'])
@permission_classes([IsAuthenticated])
def update_user(request, pk):
    try:
        user = User.objects.get(id=pk)
    except User.DoesNotExist:
        return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        serializer = UserSerializer(user)
        return Response(serializer.data)
    elif request.method == 'PUT':
        # Handle password hashing if provided
        if 'password' in request.data and request.data['password']:
            request.data['password'] = make_password(request.data['password'])

        # Prepare data for serializer
        data = request.data.copy()

        # Flatten nested agriculturist object if provided
        if 'municipal_agriculturist' in data:
            agri = data.pop('municipal_agriculturist')
            if isinstance(agri, dict):
                data.update({
                    'first_name': agri.get('first_name') or agri.get('first_name'),
                    'middle_name': agri.get('middle_name') or agri.get('middle_name', ''),
                    'last_name': agri.get('last_name') or agri.get('last_name'),
                    'sex': agri.get('sex') or agri.get('sex'),
                    'contact_number': agri.get('contact_number') or agri.get('contact_number'),
                    'position': agri.get('position') or agri.get('position'),
                    'municipality': agri.get('municipality') or agri.get('municipality'),
                })
        if 'provincial_agriculturist' in data:
            agri = data.pop('provincial_agriculturist')
            if isinstance(agri, dict):
                data.update({
                    'first_name': agri.get('first_name') or agri.get('first_name'),
                    'middle_name': agri.get('middle_name') or agri.get('middle_name', ''),
                    'last_name': agri.get('last_name') or agri.get('last_name'),
                    'sex': agri.get('sex') or agri.get('gender'),
                    'contact_number': agri.get('contact_number') or agri.get('phone_number'),
                    'position': agri.get('position') or agri.get('position'),
                })

        # Convert status string to boolean if provided as string
        if isinstance(data.get('is_active'), str):
            data['is_active'] = data['is_active'].lower() == 'true' or data['is_active'].lower() == 'active'

        serializer = UserSerializer(user, data=data, partial=True)
        if serializer.is_valid():
            user = serializer.save()
            return Response(UserSerializer(user).data, status=status.HTTP_200_OK)
        return Response({'error': 'Invalid data.', 'details': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

def check_username(request):
        username = request.GET.get('username', '')
        available = not User.objects.filter(username=username).exists()
        return JsonResponse({'available': available})

# BOATS Registry
class BoatViewSet(viewsets.ModelViewSet):
    queryset = Boat.objects.all()
    serializer_class = BoatSerializer

    def list(self, request, *args, **kwargs):
        try:
            queryset = self.filter_queryset(self.get_queryset())
            status_param = request.query_params.get('status')
            if status_param:
                if status_param.lower() == 'active':
                    queryset = queryset.filter(is_active=True)
                elif status_param.lower() == 'inactive':
                    queryset = queryset.filter(is_active=False)
            if request.query_params.get('count_only') == 'true':
                return Response({'count': queryset.count()})
            serializer = self.get_serializer(queryset, many=True)
            return Response(serializer.data)
        except Exception as e:
            print(f"Error in list action: {str(e)}")
            return Response(
                {"error": "An error occurred while fetching fisherfolk data."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def create(self, request, *args, **kwargs):
        print("Received data:", request.data)
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            print("Validation errors:", serializer.errors)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def update(self, request, *args, **kwargs):
        print("DATA RECEIVED:", request.data)
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        
        # Create a mutable copy of the request data
        mutable_data = request.data.copy()
        
        # Set the boat_id to the instance's boat_id
        mutable_data['boat_id'] = instance.boat_id
        
        serializer = self.get_serializer(instance, data=mutable_data, partial=partial)
        if serializer.is_valid():
            self.perform_update(serializer)
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def get_queryset(self):
        queryset = Boat.objects.all()
        municipality = self.request.query_params.get('municipality', None)
        if municipality is not None:
            queryset = queryset.filter(municipality=municipality)
        return queryset

    @action(detail=True, methods=['put'], url_path='archive')
    def archive(self, request, pk=None):
        try:
            boat = self.get_object()
            boat.status = 'archived'  # or whatever your archive logic is
            boat.save()
            return Response({'status': 'archived'}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        
    @action(detail=True, methods=['patch'])
    def location(self, request, pk=None):
        boat = self.get_object()
        serializer = BoatLocationUpdateSerializer(boat, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get'])
    def location_history(self, request, pk=None):
        boat = self.get_object()
        # Get the FisherfolkBoat instance for this boat
        try:
            fisherfolk_boat = FisherfolkBoat.objects.get(BoatID=boat)
            # Get location history through BoatBirukbilugTracker
            history = BoatBirukbilugTracker.objects.filter(BoatRegistryNo=fisherfolk_boat).order_by('-Timestamp')
            serializer = BoatBirukbilugTrackerSerializer(history, many=True)
            return Response(serializer.data)
        except FisherfolkBoat.DoesNotExist:
            return Response({"error": "No registered boat found"}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=False, methods=['get'])
    def by_municipality(self, request):
        boats = Boat.objects.values('municipality').annotate(
            total=models.Count('id'),
            active=models.Count('id', filter=Q(status='active')),
            inactive=models.Count('id', filter=Q(status='inactive'))
        )
        return Response(boats)

    @action(detail=False, methods=['get'])
    def by_type(self, request):
        boats = Boat.objects.values('boat_type').annotate(
            total=models.Count('id'),
            active=models.Count('id', filter=Q(status='active')),
            inactive=models.Count('id', filter=Q(status='inactive'))
        )
        return Response(boats)

    @action(detail=False, methods=['get'])
    def statistics(self, request):
        # Get total counts
        total_boats = Boat.objects.count()
        active_boats = Boat.objects.filter(status='active').count()
        inactive_boats = Boat.objects.filter(status='inactive').count()

        # Get monthly registration counts for the past 12 months
        monthly_registrations = Boat.objects.annotate(
            month=TruncMonth('created_at')
        ).values('month').annotate(
            count=models.Count('id')
        ).order_by('-month')[:12]

        return Response({
            'total_boats': total_boats,
            'active_boats': active_boats,
            'inactive_boats': inactive_boats,
            'monthly_registrations': monthly_registrations
        })

class FisherfolkViewSet(viewsets.ModelViewSet):
    queryset = Fisherfolk.objects.all()
    serializer_class = FisherfolkSerializer
    permission_classes = [IsAuthenticated]
    
    def list(self, request, *args, **kwargs):
        try:
            queryset = self.filter_queryset(self.get_queryset())
            status_param = request.query_params.get('status')
            if status_param:
                if status_param.lower() == 'active':
                    queryset = queryset.filter(is_active=True)
                elif status_param.lower() == 'inactive':
                    queryset = queryset.filter(is_active=False)
            if request.query_params.get('count_only') == 'true':
                return Response({'count': queryset.count()})
            serializer = self.get_serializer(queryset, many=True)
            return Response(serializer.data)
        except Exception as e:
            print(f"Error in list action: {str(e)}")
            return Response(
                {"error": "An error occurred while fetching fisherfolk data."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def create(self, request, *args, **kwargs):
        try:
            print("Received data:", request.data)  # Debug print
            serializer = self.get_serializer(data=request.data)
            if serializer.is_valid():
                self.perform_create(serializer)
                headers = self.get_success_headers(serializer.data)
                return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
            print("Validation errors:", serializer.errors)  # Debug print
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            print(f"Error in create action: {str(e)}")  # Debug print
            return Response(
                {"error": f"An error occurred while creating fisherfolk: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        if serializer.is_valid():
            self.perform_update(serializer)
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'])
    def search(self, request):
        query = request.query_params.get('query', '')
        if not query:
            return Response([])

        fisherfolk = Fisherfolk.objects.filter(
            models.Q(fisherfolk_number__icontains=query) |
            models.Q(registration_number__icontains=query) |
            models.Q(first_name__icontains=query) |
            models.Q(last_name__icontains=query) |
            models.Q(middle_name__icontains=query)
        ).filter(is_active=True)[:10]  # Limit to 10 results for performance

        serializer = self.get_serializer(fisherfolk, many=True)
        return Response(serializer.data)

class FisherfolkBoatViewSet(viewsets.ModelViewSet):
    queryset = FisherfolkBoat.objects.all()
    serializer_class = FisherfolkBoatSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        try:
            print("Received data:", request.data)  # Debug print
            serializer = self.get_serializer(data=request.data)
            if serializer.is_valid():
                self.perform_create(serializer)
                headers = self.get_success_headers(serializer.data)
                return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
            print("Validation errors:", serializer.errors)  # Debug print
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            print(f"Error in create action: {str(e)}")  # Debug print
            return Response(
                {"error": f"An error occurred while creating fisherfolk: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
class BirukbilugTrackerViewSet(viewsets.ModelViewSet):
    queryset = BirukbilugTracker.objects.all()
    serializer_class = BirukbilugTrackerSerializer
    permission_classes = [IsAuthenticated]

class ProvincialAgriculturistViewSet(viewsets.ModelViewSet):
    queryset = ProvincialAgriculturist.objects.all()
    serializer_class = ProvincialAgriculturistSerializer

class MunicipalAgriculturistViewSet(viewsets.ModelViewSet):
    queryset = MunicipalAgriculturist.objects.all()
    serializer_class = MunicipalAgriculturistSerializer

class ActivityLogViewSet(viewsets.ModelViewSet):
    queryset = ActivityLog.objects.all().order_by('-timestamp')
    serializer_class = ActivityLogSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def get_queryset(self):
        qs = super().get_queryset()
        count = self.request.query_params.get('count')
        if count:
            try:
                count = int(count)
                return qs[:count]
            except ValueError:
                pass
        return qs

@csrf_exempt
def gps_data(request):
    if request.method == 'POST':
        print("\n======= Incoming POST Request =======")
        print("Raw body:", request.body)
        print("Content-Type:", request.headers.get("Content-Type"))
        print("POST dict:", request.POST)

        latitude = request.POST.get('latitude')
        longitude = request.POST.get('longitude')
        boat_id = request.POST.get('boat_id')

        print("Parsed values -> Latitude:", latitude, "Longitude:", longitude, "Boat ID:", boat_id)

        try:
            gps = GPSData.objects.create(
                latitude=float(latitude),
                longitude=float(longitude),
                boat_id=int(boat_id)
            )
            return JsonResponse({'status': 'success'})
        except Exception as e:
            print("Error:", str(e))
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

    return JsonResponse({'status': 'error', 'message': 'Only POST method allowed'}, status=405)



def gps_geojson(request):
    features = []

    # You can filter per boat if needed
    gps_data = GPSData.objects.all().order_by("-timestamp")[:100]  # latest 100 points

    for gps in gps_data:
        features.append({
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [gps.longitude, gps.latitude],
            },
            "properties": {
                "boat_id": gps.boat_id,
                "timestamp": gps.timestamp.isoformat(),
            }
        })

    return JsonResponse({
        "type": "FeatureCollection",
        "features": features,
    })