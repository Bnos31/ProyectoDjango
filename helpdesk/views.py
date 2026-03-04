from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import ListView, DetailView, CreateView, UpdateView
from django.urls import reverse_lazy
from django.utils import timezone
from django.db.models import Count
from django.contrib import messages

from .models import Equipo, Incidencia, ComentarioIncidencia, AdjuntoIncidencia, AuditoriaAccion
from .forms import EquipoForm, IncidenciaCreateForm, IncidenciaUpdateAdminForm, IncidenciaUpdateTecnicoForm, ComentarioForm, AdjuntoForm
from .decorators import has_group

# Helper para loguear auditoría
def log_audit(user, accion, detalle, incidencia=None):
    AuditoriaAccion.objects.create(
        usuario=user,
        accion=accion,
        detalle=detalle,
        incidencia=incidencia
    )

@login_required
def dashboard(request):
    """
    Vista de dashboard adaptada por rol.
    ADMIN/SUPERVISOR: Todo.
    TECNICO: Solo sus incidencias.
    """
    if has_group(request.user, ['ADMIN', 'SUPERVISOR']):
        indicadores = Incidencia.objects.values('estado').annotate(total=Count('estado'))
        ultimas_incidencias = Incidencia.objects.all().order_by('-fecha_creacion')[:5]
    else:
        # TECNICO
        indicadores = Incidencia.objects.filter(tecnico_asignado=request.user).values('estado').annotate(total=Count('estado'))
        ultimas_incidencias = Incidencia.objects.filter(tecnico_asignado=request.user).order_by('-fecha_creacion')[:5]

    data_estados = { 'PENDIENTE': 0, 'EN_PROCESO': 0, 'RESUELTO': 0, 'CERRADO': 0 }
    for i in indicadores:
        data_estados[i['estado']] = i['total']

    return render(request, 'dashboard.html', {
        'data_estados': data_estados,
        'ultimas_incidencias': ultimas_incidencias,
        'is_admin_or_sup': has_group(request.user, ['ADMIN', 'SUPERVISOR'])
    })

# ============================
# INCIDENCIAS
# ============================

class IncidenciaListView(LoginRequiredMixin, ListView):
    model = Incidencia
    template_name = 'helpdesk/incidencia_list.html'
    context_object_name = 'incidencias'
    
    def get_queryset(self):
        qs = super().get_queryset()
        # Filtros por Rol
        if not has_group(self.request.user, ['ADMIN', 'SUPERVISOR']):
            # Tecnico solo ve las suyas
            qs = qs.filter(tecnico_asignado=self.request.user)
            
        # Filtros GET
        estado = self.request.GET.get('estado')
        prioridad = self.request.GET.get('prioridad')
        if estado: qs = qs.filter(estado=estado)
        if prioridad: qs = qs.filter(prioridad=prioridad)
        return qs.order_by('-fecha_creacion')

@login_required
def incidencia_detail(request, pk):
    incidencia = get_object_or_404(Incidencia, pk=pk)
    
    # Validar permisos
    is_admin_or_sup = has_group(request.user, ['ADMIN', 'SUPERVISOR'])
    if not is_admin_or_sup and incidencia.tecnico_asignado != request.user:
        messages.error(request, "No tienes permiso para ver esta incidencia.")
        return redirect('dashboard')

    if request.method == 'POST':
        action = request.POST.get('action')
        
        # Guardar comentario
        if action == 'comentar':
            c_form = ComentarioForm(request.POST)
            if c_form.is_valid():
                comentario = c_form.save(commit=False)
                comentario.incidencia = incidencia
                comentario.autor = request.user
                comentario.save()
                messages.success(request, "Comentario añadido.")
                return redirect('incidencia_detail', pk=pk)
                
        # Subir adjunto
        elif action == 'adjuntar':
            a_form = AdjuntoForm(request.POST, request.FILES)
            if a_form.is_valid():
                adjunto = a_form.save(commit=False)
                adjunto.incidencia = incidencia
                adjunto.subido_por = request.user
                adjunto.save()
                messages.success(request, "Archivo subido correctamente.")
                return redirect('incidencia_detail', pk=pk)
                
        # Cambiar estado o asignar técnico
        elif action == 'actualizar':
            if is_admin_or_sup:
                u_form = IncidenciaUpdateAdminForm(request.POST, instance=incidencia)
            else:
                u_form = IncidenciaUpdateTecnicoForm(request.POST, instance=incidencia)
                
            if u_form.is_valid():
                old_estado = incidencia.estado
                old_tecnico = incidencia.tecnico_asignado
                inc = u_form.save()
                
                # Cierre automático de fecha al poner CERRADO
                if inc.estado == 'CERRADO' and old_estado != 'CERRADO':
                    inc.fecha_cierre = timezone.now()
                    inc.save()
                
                # Auditoría
                if old_estado != inc.estado:
                    log_audit(request.user, 'CAMBIO_ESTADO', f"De {old_estado} a {inc.estado}", incidencia)
                if old_tecnico != inc.tecnico_asignado:
                    nuevo_t = inc.tecnico_asignado.username if inc.tecnico_asignado else 'Ninguno'
                    log_audit(request.user, 'ASIGNACION_TECNICO', f"Asignado a {nuevo_t}", incidencia)
                
                messages.success(request, "Incidencia actualizada.")
                return redirect('incidencia_detail', pk=pk)

    # Contexto GET
    comentarios = incidencia.comentarios.all().order_by('-created_at')
    adjuntos = incidencia.adjuntos.all()
    
    c_form = ComentarioForm()
    a_form = AdjuntoForm()
    u_form = IncidenciaUpdateAdminForm(instance=incidencia) if is_admin_or_sup else IncidenciaUpdateTecnicoForm(instance=incidencia)

    return render(request, 'helpdesk/incidencia_detail.html', {
        'incidencia': incidencia,
        'comentarios': comentarios,
        'adjuntos': adjuntos,
        'c_form': c_form,
        'a_form': a_form,
        'u_form': u_form,
        'is_admin_or_sup': is_admin_or_sup
    })

class IncidenciaCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    model = Incidencia
    form_class = IncidenciaCreateForm
    template_name = 'helpdesk/incidencia_form.html'
    success_url = reverse_lazy('incidencia_list')
    
    def test_func(self):
        return has_group(self.request.user, ['ADMIN', 'SUPERVISOR'])
        
    def form_valid(self, form):
        form.instance.creado_por = self.request.user
        response = super().form_valid(form)
        log_audit(self.request.user, 'CREACION_INCIDENCIA', f"Creada incidencia {self.object.codigo}", self.object)
        messages.success(self.request, "Incidencia creada.")
        return response

# ============================
# EQUIPOS
# ============================
class EquipoListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    model = Equipo
    template_name = 'helpdesk/equipo_list.html'
    context_object_name = 'equipos'
    
    def test_func(self):
        return has_group(self.request.user, ['ADMIN', 'SUPERVISOR'])

class EquipoCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    model = Equipo
    form_class = EquipoForm
    template_name = 'helpdesk/equipo_form.html'
    success_url = reverse_lazy('equipo_list')
    
    def test_func(self):
        return has_group(self.request.user, ['ADMIN', 'SUPERVISOR'])

class EquipoUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Equipo
    form_class = EquipoForm
    template_name = 'helpdesk/equipo_form.html'
    success_url = reverse_lazy('equipo_list')
    
    def test_func(self):
        return has_group(self.request.user, ['ADMIN', 'SUPERVISOR'])

# ============================
# REPORTES
# ============================
@login_required
def reportes(request):
    if not has_group(request.user, ['ADMIN', 'SUPERVISOR']):
        messages.error(request, "Acceso denegado a reportes.")
        return redirect('dashboard')
        
    conteo_estados = Incidencia.objects.values('estado').annotate(total=Count('estado'))
    conteo_tecnicos = Incidencia.objects.exclude(tecnico_asignado=None).values('tecnico_asignado__username').annotate(total=Count('id'))
    conteo_equipos = Incidencia.objects.values('equipo__nombre').annotate(total=Count('id'))
    
    auditoria = AuditoriaAccion.objects.all().order_by('-created_at')[:20]

    return render(request, 'helpdesk/reportes.html', {
        'conteo_estados': conteo_estados,
        'conteo_tecnicos': conteo_tecnicos,
        'conteo_equipos': conteo_equipos,
        'auditoria': auditoria,
    })
