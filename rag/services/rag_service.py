"""
rag_service.py — Servicio central de RAG: indexación de PDFs y consulta con LLM.

Flujo de indexación:
    PDF → PyPDFLoader → RecursiveCharacterTextSplitter → OllamaEmbeddings → ChromaDB

Flujo de consulta:
    pregunta → OllamaEmbeddings → ChromaDB similarity search → contexto → OllamaLLM → respuesta
"""

import logging
from django.conf import settings

logger = logging.getLogger(__name__)

COLLECTION_NAME = 'helpdesk_docs'


def _get_chromadb_client():
    """Retorna cliente HTTP de ChromaDB."""
    import chromadb
    host = getattr(settings, 'CHROMADB_HOST', 'localhost')
    port = int(getattr(settings, 'CHROMADB_PORT', 8001))
    return chromadb.HttpClient(host=host, port=port)


def _get_embeddings():
    """Retorna la función de embeddings usando Ollama."""
    from langchain_ollama import OllamaEmbeddings
    return OllamaEmbeddings(
        model=getattr(settings, 'OLLAMA_MODEL', 'llama3.2:1b'),
        base_url=getattr(settings, 'OLLAMA_BASE_URL', 'http://localhost:11434'),
    )


def _get_vectorstore(chroma_client=None):
    """Retorna el vector store de Chroma conectado al cliente HTTP."""
    from langchain_chroma import Chroma
    if chroma_client is None:
        chroma_client = _get_chromadb_client()
    return Chroma(
        client=chroma_client,
        collection_name=COLLECTION_NAME,
        embedding_function=_get_embeddings(),
    )


def check_services():
    """
    Verifica disponibilidad de ChromaDB y Ollama.
    Returns: (ok: bool, error_msg: str | None)
    """
    import requests as req

    try:
        client = _get_chromadb_client()
        client.heartbeat()
    except Exception as e:
        return False, f"ChromaDB no disponible en {settings.CHROMADB_HOST}:{settings.CHROMADB_PORT} — {e}"

    try:
        ollama_url = getattr(settings, 'OLLAMA_BASE_URL', 'http://localhost:11434')
        resp = req.get(f'{ollama_url}/api/tags', timeout=5)
        resp.raise_for_status()
    except Exception as e:
        return False, f"Ollama no disponible en {settings.OLLAMA_BASE_URL} — {e}"

    return True, None


def indexar_documento(documento_rag):
    """
    Extrae texto de un PDF, lo divide en chunks y los guarda en ChromaDB.

    Args:
        documento_rag: instancia de DocumentoRAG (con archivo guardado en disco)

    Returns:
        int: número de chunks indexados

    Raises:
        FileNotFoundError, ValueError, Exception
    """
    import os
    from langchain_community.document_loaders import PyPDFLoader
    from langchain.text_splitter import RecursiveCharacterTextSplitter

    archivo_path = documento_rag.archivo.path
    if not os.path.exists(archivo_path):
        raise FileNotFoundError(f"Archivo no encontrado: {archivo_path}")

    logger.info(f"[RAG] Cargando PDF: {archivo_path}")
    loader = PyPDFLoader(archivo_path)
    pages = loader.load()

    if not pages:
        raise ValueError("El PDF no tiene contenido de texto extraíble.")

    logger.info(f"[RAG] {len(pages)} páginas cargadas")

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        length_function=len,
    )
    chunks = splitter.split_documents(pages)

    for chunk in chunks:
        chunk.metadata['documento_id'] = str(documento_rag.id)
        chunk.metadata['documento_nombre'] = documento_rag.nombre

    logger.info(f"[RAG] {len(chunks)} chunks generados")

    vectorstore = _get_vectorstore()
    vectorstore.add_documents(chunks)

    logger.info(f"[RAG] Indexación completada: {len(chunks)} chunks en ChromaDB")
    return len(chunks)


def consultar_rag(pregunta: str) -> dict:
    """
    Realiza una consulta RAG completa: retrieval + generación con Ollama.

    Args:
        pregunta: texto de la consulta del usuario

    Returns:
        dict con 'respuesta' (str) y 'fuentes' (list[dict])

    Raises:
        Exception si ChromaDB u Ollama no están disponibles
    """
    from langchain_ollama import OllamaLLM
    from langchain.chains import RetrievalQA
    from langchain_core.prompts import PromptTemplate

    ollama_url = getattr(settings, 'OLLAMA_BASE_URL', 'http://localhost:11434')
    model = getattr(settings, 'OLLAMA_MODEL', 'llama3.2:1b')

    llm = OllamaLLM(
        model=model,
        base_url=ollama_url,
        temperature=0.1,
    )

    vectorstore = _get_vectorstore()
    retriever = vectorstore.as_retriever(
        search_type='similarity',
        search_kwargs={'k': 4},
    )

    prompt_template = """Eres un asistente técnico especializado en mantenimiento industrial.
Usa ÚNICAMENTE el siguiente contexto extraído de los manuales técnicos para responder.
Si la información no aparece en el contexto, responde: "No encontré esa información en los documentos disponibles."
Responde siempre en español, de forma clara y concisa.

Contexto:
{context}

Pregunta: {question}

Respuesta:"""

    prompt = PromptTemplate(
        template=prompt_template,
        input_variables=['context', 'question'],
    )

    chain = RetrievalQA.from_chain_type(
        llm=llm,
        chain_type='stuff',
        retriever=retriever,
        chain_type_kwargs={'prompt': prompt},
        return_source_documents=True,
    )

    logger.info(f"[RAG] Consultando: {pregunta[:80]}")
    result = chain.invoke({'query': pregunta})
    logger.info("[RAG] Respuesta generada")

    fuentes_vistas = set()
    fuentes = []
    for doc in result.get('source_documents', []):
        clave = (
            doc.metadata.get('documento_nombre', 'Desconocido'),
            doc.metadata.get('page', '?'),
        )
        if clave not in fuentes_vistas:
            fuentes_vistas.add(clave)
            pagina = doc.metadata.get('page', 0)
            fuentes.append({
                'documento': doc.metadata.get('documento_nombre', 'Desconocido'),
                'pagina': int(pagina) + 1 if isinstance(pagina, (int, float)) else pagina,
            })

    return {
        'respuesta': result.get('result', '').strip(),
        'fuentes': fuentes,
    }


def eliminar_vectores_documento(documento_id: int):
    """
    Elimina todos los vectores de un documento en ChromaDB.
    Falla silenciosamente si ChromaDB no está disponible.
    """
    try:
        client = _get_chromadb_client()
        try:
            collection = client.get_collection(COLLECTION_NAME)
            collection.delete(where={'documento_id': str(documento_id)})
            logger.info(f"[RAG] Vectores del documento {documento_id} eliminados")
        except Exception:
            pass
    except Exception as e:
        logger.warning(f"[RAG] No se pudieron eliminar vectores de {documento_id}: {e}")
