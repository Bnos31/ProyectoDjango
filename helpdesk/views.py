from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import ListView, DetailView, CreateView, UpdateView
from django.urls import reverse_lazy
from django.utils import timezone
from django.db.models import Count
from django.contrib import messages

from .models import Equipo, Incidencia, ComentarioIncidencia, AdjuntoIncidencia, AuditoriaAccion
from .forms import EquipoForm, IncidenciaCreateForm, IncidenciaUpdateAdminForm, IncidenciaUpdateTecnicoForm, ComentarioForm, AdjuntoForm, ImportDatasetForm
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
# MACHINE LEARNING — IMPORTACIÓN DE DATASET
# ============================
@login_required
def import_dataset_view(request):
    """
    Vista para que el usuario cargue el dataset Excel desde el navegador.
    Solo accesible por ADMIN y SUPERVISOR.
    """
    import io
    import pandas as pd
    from datetime import timedelta

    if not has_group(request.user, ['ADMIN', 'SUPERVISOR']):
        messages.error(request, "Acceso denegado.")
        return redirect('dashboard')

    CRITICIDAD_MAP = {'Alta': 'ALTA', 'Media': 'MEDIA', 'Baja': 'BAJA', 'Crítica': 'CRITICA', 'Critica': 'CRITICA'}
    ESTADO_MAP = {'Cerrado': 'CERRADO', 'Pendiente': 'PENDIENTE', 'En Proceso': 'EN_PROCESO', 'Resuelto': 'RESUELTO'}

    form = ImportDatasetForm()

    if request.method == 'POST':
        form = ImportDatasetForm(request.POST, request.FILES)
        if form.is_valid():
            archivo = request.FILES['archivo']
            limpiar = form.cleaned_data['limpiar_datos']

            # Validar extensión
            if not archivo.name.endswith(('.xlsx', '.xls')):
                messages.error(request, "El archivo debe ser un Excel (.xlsx o .xls).")
                return render(request, 'helpdesk/import_dataset.html', {'form': form})

            try:
                df = pd.read_excel(io.BytesIO(archivo.read()))
            except Exception as e:
                messages.error(request, f"Error al leer el archivo Excel: {e}")
                return render(request, 'helpdesk/import_dataset.html', {'form': form})

            # Renombrar columnas para trabajar sin problemas de encoding
            if len(df.columns) < 12:
                messages.error(request, f"El archivo tiene {len(df.columns)} columnas, se esperan 12.")
                return render(request, 'helpdesk/import_dataset.html', {'form': form})

            df.columns = [
                'id_activo', 'nombre_equipo', 'marca_modelo', 'ubicacion',
                'fecha_incidencia', 'tipo_mant', 'falla_detectada',
                'causa_raiz', 'accion_correctiva', 'repuestos',
                'criticidad', 'estado',
            ]

            # Limpiar datos existentes si se solicitó
            if limpiar:
                Incidencia.objects.all().delete()
                Equipo.objects.all().delete()

            # Usuario del sistema como creador
            system_user = request.user

            equipos_creados = equipos_existentes = incidencias_creadas = errores = 0

            for idx, row in df.iterrows():
                try:
                    codigo = str(row['id_activo']).strip()
                    nombre = str(row['nombre_equipo']).strip()
                    ubicacion = str(row['ubicacion']).strip() if pd.notna(row['ubicacion']) else ''

                    equipo, created = Equipo.objects.get_or_create(
                        codigo=codigo,
                        defaults={'nombre': nombre, 'ubicacion': ubicacion, 'activo': True},
                    )
                    if created:
                        equipos_creados += 1
                    else:
                        equipos_existentes += 1

                    prioridad = CRITICIDAD_MAP.get(str(row['criticidad']).strip(), 'MEDIA')
                    estado = ESTADO_MAP.get(str(row['estado']).strip(), 'CERRADO')

                    tipo_mant = str(row['tipo_mant']).strip() if pd.notna(row['tipo_mant']) else ''
                    falla = str(row['falla_detectada']).strip() if pd.notna(row['falla_detectada']) else ''
                    causa = str(row['causa_raiz']).strip() if pd.notna(row['causa_raiz']) else ''
                    accion = str(row['accion_correctiva']).strip() if pd.notna(row['accion_correctiva']) else ''
                    repuestos = str(row['repuestos']).strip() if pd.notna(row['repuestos']) else ''
                    marca = str(row['marca_modelo']).strip() if pd.notna(row['marca_modelo']) else ''

                    titulo = f"[{tipo_mant}] {falla}" if falla else f"[{tipo_mant}] Incidencia"
                    descripcion = (
                        f"Causa raiz: {causa}\n"
                        f"Accion correctiva: {accion}\n"
                        f"Repuestos: {repuestos}\n"
                        f"Marca/Modelo: {marca}"
                    )

                    fecha = row['fecha_incidencia']
                    if pd.isna(fecha):
                        fecha = timezone.now()
                    else:
                        fecha = pd.Timestamp(fecha).to_pydatetime()
                        if timezone.is_naive(fecha):
                            fecha = timezone.make_aware(fecha)

                    fecha_cierre = fecha + timedelta(days=1) if estado in ['CERRADO', 'RESUELTO'] else None

                    inc = Incidencia(
                        titulo=titulo[:200],
                        descripcion=descripcion,
                        prioridad=prioridad,
                        estado=estado,
                        equipo=equipo,
                        creado_por=system_user,
                        tecnico_asignado=None,
                        fecha_cierre=fecha_cierre,
                    )
                    inc.save()
                    Incidencia.objects.filter(pk=inc.pk).update(
                        fecha_creacion=fecha,
                        created_at=fecha,
                    )
                    incidencias_creadas += 1

                except Exception:
                    errores += 1

            resumen = {
                'equipos_creados': equipos_creados,
                'equipos_existentes': equipos_existentes,
                'incidencias_creadas': incidencias_creadas,
                'errores': errores,
                'total': len(df),
            }
            messages.success(
                request,
                f"Importacion completada: {incidencias_creadas} incidencias y "
                f"{equipos_creados} equipos nuevos importados."
            )
            return render(request, 'helpdesk/import_dataset.html', {'form': ImportDatasetForm(), 'resumen': resumen})

    return render(request, 'helpdesk/import_dataset.html', {'form': form})


# ============================
# MACHINE LEARNING — PREDICCIÓN DE FALLAS
# ============================
@login_required
def predict_equipment_failure(request, equipo_id):
    """
    Vista que predice la probabilidad de falla crítica de un equipo.
    Usa el módulo ML con el modelo entrenado (model.pkl).
    """
    from .ml.predict import predict_failure

    equipo = get_object_or_404(Equipo, pk=equipo_id)

    # Obtener la incidencia más reciente del equipo para usar sus features
    ultima_incidencia = (
        equipo.incidencias
        .order_by('-fecha_creacion')
        .first()
    )

    if not ultima_incidencia:
        messages.warning(
            request,
            f"El equipo '{equipo.nombre}' no tiene incidencias registradas. "
            "Importa el dataset primero."
        )
        return redirect('equipo_list')

    # Preparar features para la predicción
    tecnico = (
        ultima_incidencia.tecnico_asignado.username
        if ultima_incidencia.tecnico_asignado
        else 'Sin asignar'
    )

    if ultima_incidencia.fecha_cierre and ultima_incidencia.fecha_creacion:
        dias_resolucion = max(
            (ultima_incidencia.fecha_cierre - ultima_incidencia.fecha_creacion).days, 0
        )
    else:
        dias_resolucion = -1

    data = {
        'equipo': equipo.nombre,
        'estado': ultima_incidencia.estado,
        'tecnico_asignado': tecnico,
        'mes_reporte': ultima_incidencia.fecha_creacion.month,
        'dia_semana': ultima_incidencia.fecha_creacion.weekday(),
        'dias_resolucion': dias_resolucion,
    }

    try:
        resultado = predict_failure(data)
    except FileNotFoundError:
        messages.error(
            request,
            "El modelo ML no está entrenado todavía. "
            "Ejecuta: python manage.py shell → from helpdesk.ml.train_model import train_model → train_model()"
        )
        return redirect('equipo_list')

    # Estadísticas de incidencias históricas del equipo
    total_incidencias = equipo.incidencias.count()
    incidencias_criticas = equipo.incidencias.filter(prioridad__in=['ALTA', 'CRITICA']).count()

    return render(request, 'helpdesk/predict_failure.html', {
        'equipo': equipo,
        'resultado': resultado,
        'ultima_incidencia': ultima_incidencia,
        'total_incidencias': total_incidencias,
        'incidencias_criticas': incidencias_criticas,
    })


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
