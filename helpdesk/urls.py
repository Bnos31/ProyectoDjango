from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    # Auth
    path('login/', auth_views.LoginView.as_view(template_name='login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    
    # Dashboard
    path('', views.dashboard, name='dashboard'),
    
    # Incidencias
    path('incidencias/', views.IncidenciaListView.as_view(), name='incidencia_list'),
    path('incidencias/crear/', views.IncidenciaCreateView.as_view(), name='incidencia_crear'),
    path('incidencias/<int:pk>/', views.incidencia_detail, name='incidencia_detail'),
    
    # Equipos
    path('equipos/', views.EquipoListView.as_view(), name='equipo_list'),
    path('equipos/crear/', views.EquipoCreateView.as_view(), name='equipo_crear'),
    path('equipos/<int:pk>/editar/', views.EquipoUpdateView.as_view(), name='equipo_editar'),
    
    # Reportes
    path('reportes/', views.reportes, name='reportes'),
]
