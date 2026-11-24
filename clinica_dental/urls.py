from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('index/', views.index, name='index_page'),
    path('index', views.index),
    path('main/', views.main, name='main.html'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    # Citas médicas
    path('citas/crear/', views.cita_crear, name='cita_crear'),
    path('citas/<int:id_cita>/editar/', views.cita_editar, name='cita_editar'),
    path('citas/<int:id_cita>/eliminar/', views.cita_eliminar, name='cita_eliminar'),
    # Pacientes
    path('pacientes/', views.pacientes_view, name='pacientes'),
    path('pacientes/crear/', views.paciente_crear, name='paciente_crear'),
    path('pacientes/<int:id_paciente>/editar/', views.paciente_editar, name='paciente_editar'),
]
