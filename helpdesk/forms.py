from django import forms
from .models import Equipo, Incidencia, ComentarioIncidencia, AdjuntoIncidencia, DocumentoRAG
from django.contrib.auth.models import User

class EquipoForm(forms.ModelForm):
    class Meta:
        model = Equipo
        fields = ['codigo', 'nombre', 'ubicacion', 'activo']

class IncidenciaCreateForm(forms.ModelForm):
    class Meta:
        model = Incidencia
        fields = ['titulo', 'descripcion', 'prioridad', 'equipo']

class IncidenciaUpdateAdminForm(forms.ModelForm):
    class Meta:
        model = Incidencia
        fields = ['prioridad', 'estado', 'tecnico_asignado']
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Limitar campo técnico asignado al grupo TECNICO
        self.fields['tecnico_asignado'].queryset = User.objects.filter(groups__name='TECNICO', is_active=True)

class IncidenciaUpdateTecnicoForm(forms.ModelForm):
    class Meta:
        model = Incidencia
        fields = ['estado'] # Técnicos solo pueden cambiar estado
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Técnicos no pueden cerrar la incidencia o dejarla pendiente de nuevo libremente (depende lógica de negocio)
        # Ocultaremos CERRADO para técnicos, el supervisor la cierra.
        choices = [
            ('EN_PROCESO', 'En Proceso'),
            ('RESUELTO', 'Resuelto')
        ]
        self.fields['estado'].choices = choices

class ComentarioForm(forms.ModelForm):
    class Meta:
        model = ComentarioIncidencia
        fields = ['comentario']
        widgets = {
            'comentario': forms.Textarea(attrs={'rows': 3}),
        }

class AdjuntoForm(forms.ModelForm):
    class Meta:
        model = AdjuntoIncidencia
        fields = ['archivo']

class DocumentoUploadForm(forms.ModelForm):
    class Meta:
        model = DocumentoRAG
        fields = ['archivo']
        
class ChatForm(forms.Form):
    pregunta = forms.CharField(
        widget=forms.TextInput(attrs={'placeholder': 'Escribe tu pregunta aquí...', 'class': 'form-control'}),
        label=''
    )
