"""HTTP endpoints. Build/cache logic lives in services/builds.py."""
from django.http import FileResponse, JsonResponse, HttpResponse, HttpRequest
import threading

from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from home.models import App, Category, Build, Firmware, BuildJob
from .serializers import AppSerializer, CategorySerializer
from .sync import start_sync, stop_sync
from .services.builds import run_build_job, get_or_build
from .services.git import get_remote_commit

@api_view(["GET"])
def app_list(request: HttpRequest) -> Response:
    """List apps, optionally filtered by category and sliced by index/shift/max_count."""
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

    return Response(AppSerializer(apps, many=True).data)

@api_view(["GET"])
def app_detail(request: HttpRequest, app_id) -> Response:
    """Retrieve a single app by primary key."""
    try:
        app = App.objects.get(pk=app_id)
    except App.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)
    return Response(AppSerializer(app).data)

@api_view(["GET"])
def app_manifest(request, app_id):
    """Generate a minimal .fim installation manifest for an app.

    The SDK only produces the binary .fapmeta inside the .fap; the text .fim in
    /ext/apps_manifests/ is written by the installer, so we replicate
    it. Mainly for detection of installed and updatable apps.
    """
    app = App.objects.filter(id=app_id).first()
    if not app:
        return JsonResponse({"error": "app not found"}, status=404)

    api = request.query_params.get("api", "0.0")
    path = f"/ext/apps/{app.category.name}/{app.fap_id}.fap"
    build_row = Build.objects.filter(app=app, firmware_id=request.query_params.get("firmware")).first()
    commit = build_row.commit if build_row else ""

    manifest = "\n".join([
        "Filetype: Flipper Application Installation Manifest",
        "Version: 1",
        f"Full Name: {app.name}",
        f"Version Build API: {api}",
        f"Build Commit: {commit}",      # custom field - for our update detection (shouldn't cause issues)
        f"Path: {path}",
        "",
    ])
    return HttpResponse(manifest, content_type="text/plain")

@api_view(["GET"])
def app_current_commit(request, app_id):
    """The latest upstream commit for an app (for update detection)."""
    app = App.objects.filter(id=app_id).first()
    if not app:
        return JsonResponse({"error": "app not found"}, status=404)
    commit = get_remote_commit(app.location_origin, app.branch or "main") or ""
    return JsonResponse({"commit": commit})

@api_view(["GET"])
def category_list(request: HttpRequest) -> Response:
    """List all categories."""
    return Response(CategorySerializer(Category.objects.all(), many=True).data)

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

def _fap_response(build_row, app_name: str) -> FileResponse:
    """Serve a cached Build's .fap as a download."""
    resp = FileResponse(build_row.file.open("rb"), content_type="application/octet-stream")
    resp["Content-Disposition"] = f'attachment; filename="{app_name}.fap"'
    if build_row.md5:
        resp["X-Fap-Md5"] = build_row.md5
    return resp


def _resolve_firmware(request):
    """The firmware to build for: the requested one, else the first configured."""
    fw_id = request.query_params.get("firmware")
    return Firmware.objects.filter(id=fw_id).first() or Firmware.objects.first()

@api_view(["POST"])
def app_build_start(request, app_id):
    """Start a background build (or report it's already cached). Returns a job id."""
    firmware = _resolve_firmware(request)
    app = App.objects.filter(id=app_id).first()
    if not app or not firmware:
        return JsonResponse({"error": "app or firmware not found"}, status=404)

    cached = Build.objects.filter(app=app, firmware=firmware).first()
    if cached and cached.file and cached.file.storage.exists(cached.file.name):
        return JsonResponse({"status": "done", "cached": True})

    job = BuildJob.objects.create(app=app, firmware=firmware, status="pending")
    threading.Thread(target=run_build_job, args=(job.id,), daemon=True).start()
    return JsonResponse({"job_id": job.id, "status": "pending"})

@api_view(["GET"])
def app_build_status(request, job_id):
    """Poll a build job's progress."""
    job = BuildJob.objects.filter(id=job_id).first()
    if not job:
        return JsonResponse({"error": "job not found"}, status=404)
    return JsonResponse({
        "status": job.status,
        "percent": job.percent,
        "message": job.message,
        "error": job.error,
    })

@api_view(["GET"])
def app_download(request, app_id):
    """Serve an app's .fap, building it synchronously on a cache miss."""
    firmware = _resolve_firmware(request)
    if not firmware:
        return JsonResponse({"error": "no firmware configured"}, status=400)
    app = App.objects.filter(id=app_id).first()
    if not app:
        return JsonResponse({"error": "app not found"}, status=404)

    cached = Build.objects.filter(app=app, firmware=firmware).first()
    if cached and cached.file and cached.file.storage.exists(cached.file.name):
        return _fap_response(cached, app.name)
    if cached:
        cached.delete()  # stale row: file went missing → rebuild below

    build_row, err = get_or_build(app.id, firmware.id)
    if not build_row:
        return JsonResponse({"error": f"build failed: {err}"}, status=502)
    return _fap_response(build_row, app.name)

@api_view(["GET"])
def sync_manifests(request: HttpRequest) -> Response:
    """Start a background manifest sync. Returns immediately."""
    started = start_sync()
    return Response({
        "success": started,
        "message": "Sync started in background" if started else "No manifests available or error occurred",
    })

@api_view(["GET"])
def sync_stop(request: HttpRequest) -> Response:
    """Request cancellation of a running sync."""
    stopped = stop_sync()
    return Response({
        "success": stopped,
        "message": "Sync cancellation requested" if stopped else "No sync was running",
    })
