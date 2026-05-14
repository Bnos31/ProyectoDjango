from django import forms
from .models import DocumentoRAG


class UploadDocumentoForm(forms.ModelForm):
    class Meta:
        model = DocumentoRAG
        fields = ['nombre', 'archivo']
        widgets = {
            'nombre': forms.TextInput(attrs={
                'placeholder': 'Ej: Manual de Mantenimiento Motor Eléctrico',
                'class': 'form-control',
            }),
            'archivo': forms.FileInput(attrs={
                'accept': '.pdf',
                'class': 'form-control',
            }),
        }
        labels = {
            'nombre': 'Nombre del documento',
            'archivo': 'Archivo PDF',
        }

    def clean_archivo(self):
        archivo = self.cleaned_data.get('archivo')
        if archivo:
            if not archivo.name.lower().endswith('.pdf'):
                raise forms.ValidationError("Solo se permiten archivos PDF.")
            if archivo.size > 50 * 1024 * 1024:
                raise forms.ValidationError("El archivo no puede superar los 50 MB.")
        return archivo
