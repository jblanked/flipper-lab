from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import redirect, render

from .models import App, Category

def app(request: HttpRequest, fap_id: str) -> HttpResponse:
    """View for an app page."""
    app_object = App.objects.filter(fap_id=fap_id).first()
    if not app_object:
        print(f'App with fap_id {fap_id} not found')
        return redirect('apps')
    return render(request, 'app.html', {'app': app_object})

def apps(request: HttpRequest, category_name: str = None) -> HttpResponse:
    """View for the apps page."""
    app_objects = App.objects.all()
    all_categories = Category.objects.all()
    active_category = None
    template = 'apps.html'
    if category_name:
        active_category = Category.objects.filter(name__iexact=category_name).first()
        if active_category:
            app_objects = app_objects.filter(category=active_category)
        template = 'category.html'
    return render(request, template, {
        'apps': app_objects,
        'categories': all_categories,
        'active_category': active_category,
    })

def home(request: HttpRequest) -> HttpResponse:
    """View for the home page."""
    total_apps = App.objects.count()
    total_categories = Category.objects.count()
    featured_apps = App.objects.all()[:6]
    return render(request, 'home.html', {
        'total_apps': total_apps,
        'total_categories': total_categories,
        'featured_apps': featured_apps,
    })

def upload(request: HttpRequest) -> HttpResponse:
    """Post request to start uploading an app to a connected Flipper Zero."""
    if request.method == 'POST':
        fap_id = request.POST.get('fap_id')
        app_object = App.objects.filter(fap_id=fap_id).first()
        if not app_object:
            print(f'App with fap_id {fap_id} not found')
            return JsonResponse({'error': 'App not found'}, status=404)
        
        # will add logic here
        print(f'Uploading app with fap_id {fap_id}')
        return JsonResponse({'message': 'Upload started'})

    return JsonResponse({'error': 'Invalid request method'}, status=400)