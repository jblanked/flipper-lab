from django.http import HttpRequest
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from home.models import App, Category

from .serializers import AppSerializer, CategorySerializer
from .sync import start_sync, stop_sync

@api_view(["GET"])
def app_detail(request: HttpRequest, app_id) -> Response:
    """Retrieve a single app by its primary key."""
    try:
        app = App.objects.get(pk=app_id)
    except App.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)
    serializer = AppSerializer(app)
    return Response(serializer.data)


@api_view(["GET"])
def app_download(request: HttpRequest, app_id) -> Response:
    """Return app data for download."""
    try:
        app = App.objects.get(pk=app_id)
    except App.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)
    serializer = AppSerializer(app)
    return Response(serializer.data)

@api_view(["GET"])
def app_list(request: HttpRequest) -> Response:
    """List apps with optional category filter and pagination."""
    apps = App.objects.all()
    category_id = request.query_params.get("category_id")
    if category_id:
        apps = apps.filter(category_id=category_id)
    index = request.query_params.get("index")
    shift = request.query_params.get("shift")
    if index is not None and shift is not None:
        try:
            apps = apps[int(index):int(index) + int(shift)]
        except (ValueError, IndexError):
            pass
    max_count = request.query_params.get("max_count")
    if max_count:
        try:
            apps = apps[:int(max_count)]
        except ValueError:
            pass
    serializer = AppSerializer(apps, many=True)
    return Response(serializer.data)

@api_view(["GET"])
def category_list(request: HttpRequest) -> Response:
    """List all categories ordered by my_order."""
    categories = Category.objects.all()
    serializer = CategorySerializer(categories, many=True)
    return Response(serializer.data)

@api_view(["POST"])
def new_app(request: HttpRequest) -> Response:
    """Create a new app."""
    serializer = AppSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(["POST"])
def new_category(request: HttpRequest) -> Response:
    """Create a new category."""
    serializer = CategorySerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(["GET"])
def sync_stop(request: HttpRequest) -> Response:
    """Request cancellation of the currently running sync, if any."""
    stopped = stop_sync()
    return Response({
        "success": stopped,
        "message": "Sync cancellation requested" if stopped else "No sync was running",
    })

@api_view(["GET"])
def sync_manifests(request: HttpRequest) -> Response:
    """Sync all app manifests in a background thread. Returns immediately."""
    started = start_sync()
    return Response({"success": started, "message": "Sync started in background" if started else "No manifests available or error occurred"})
    