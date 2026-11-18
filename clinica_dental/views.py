from functools import wraps
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.shortcuts import (
    render,
    redirect,
    get_object_or_404
)
from .models import AsistenteDental
from .models import Doctor

# Create your views here.
def main(request):
    return render(request, 'main.html')

def index(request):
    return render(request, 'index.html')    