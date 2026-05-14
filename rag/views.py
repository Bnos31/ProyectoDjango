import json
import logging

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from helpdesk.decorators import has_group
from .models import DocumentoRAG, ConsultaRAG
from .forms import UploadDocumentoForm

logger = logging.getLogger(__name__)


@login_required
def upload_documento(request):
    """Sube un PDF y lo indexa en ChromaDB."""
    if request.method == 'POST':
        form = UploadDocumentoForm(request.POST, request.FILES)
        if form.is_valid():
            doc = form.save(commit=False)
            doc.subido_por = request.user
            doc.estado = 'indexando'
            doc.save()

            try:
                from .services.rag_service import indexar_documento
                num_chunks = indexar_documento(doc)
                doc.num_chunks = num_chunks
                doc.estado = 'indexado'
                doc.error_mensaje = None
                doc.save()
                messages.success(
                    request,
                    f"'{doc.nombre}' indexado correctamente ({num_chunks} fragmentos)."
                )
            except Exception as e:
                doc.estado = 'error'
                doc.error_mensaje = str(e)
                doc.save()
                logger.error(f"[RAG] Error al indexar documento {doc.id}: {e}", exc_info=True)
                messages.error(
                    request,
                    f"Error al indexar '{doc.nombre}': {e}. "
                    "Verifica que ChromaDB y Ollama estén activos."
                )

            return redirect('rag:documentos')
    else:
        form = UploadDocumentoForm()

    return render(request, 'rag/upload.html', {'form': form})


@login_required
def lista_documentos(request):
    """Lista todos los documentos RAG subidos."""
    documentos = DocumentoRAG.objects.all()
    indexados = documentos.filter(estado='indexado').count()
    return render(request, 'rag/documentos.html', {
        'documentos': documentos,
        'total': documentos.count(),
        'indexados': indexados,
    })


@login_required
def eliminar_documento(request, pk):
    """Elimina un documento y sus vectores de ChromaDB."""
    if not has_group(request.user, ['ADMIN', 'SUPERVISOR']):
        messages.error(request, "Acceso denegado.")
        return redirect('rag:documentos')

    doc = get_object_or_404(DocumentoRAG, pk=pk)
    nombre = doc.nombre

    try:
        from .services.rag_service import eliminar_vectores_documento
        eliminar_vectores_documento(doc.id)
    except Exception as e:
        logger.warning(f"[RAG] No se eliminaron vectores de {pk}: {e}")

    if doc.archivo:
        try:
            doc.archivo.delete(save=False)
        except Exception:
            pass

    doc.delete()
    messages.success(request, f"Documento '{nombre}' eliminado.")
    return redirect('rag:documentos')


@login_required
def chat_rag(request):
    """Interfaz principal de chat RAG."""
    historial = ConsultaRAG.objects.filter(usuario=request.user).order_by('-created_at')[:10]
    documentos_indexados = DocumentoRAG.objects.filter(estado='indexado').count()

    return render(request, 'rag/chat.html', {
        'historial': historial,
        'documentos_indexados': documentos_indexados,
    })


@login_required
@require_POST
def consultar_ajax(request):
    """Endpoint AJAX para consultas RAG. Retorna JSON."""
    try:
        body = json.loads(request.body)
        pregunta = body.get('pregunta', '').strip()
    except Exception:
        return JsonResponse({'error': 'JSON inválido.'}, status=400)

    if not pregunta:
        return JsonResponse({'error': 'La pregunta no puede estar vacía.'}, status=400)

    documentos_indexados = DocumentoRAG.objects.filter(estado='indexado').count()
    if documentos_indexados == 0:
        return JsonResponse({
            'error': 'No hay documentos indexados. Sube un PDF primero en la sección "Documentos".'
        }, status=400)

    try:
        from .services.rag_service import consultar_rag
        resultado = consultar_rag(pregunta)

        ConsultaRAG.objects.create(
            pregunta=pregunta,
            respuesta=resultado['respuesta'],
            fuentes=json.dumps(resultado['fuentes'], ensure_ascii=False),
            usuario=request.user,
        )

        return JsonResponse({
            'respuesta': resultado['respuesta'],
            'fuentes': resultado['fuentes'],
        })

    except Exception as e:
        logger.error(f"[RAG] Error en consulta: {e}", exc_info=True)
        return JsonResponse({
            'error': f"Error al consultar: {e}. Verifica que Ollama y ChromaDB estén activos."
        }, status=500)
