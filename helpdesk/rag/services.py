import os
from django.conf import settings
from langchain_community.document_loaders import PyPDFLoader, Docx2txtLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.llms import Ollama
from langchain.chains import RetrievalQA

def get_llm():
    """
    Inicializa y retorna el LLM local vía Ollama.
    Apunta al endpoint configurado en settings (ej. http://ollama:11434).
    """
    return Ollama(
        base_url=settings.OLLAMA_BASE_URL,
        model=settings.OLLAMA_MODEL,
        temperature=0
    )

def load_documents(file_path):
    """
    Carga documentos dependiendo de su extensión (PDF, DOCX, TXT)
    y retorna la lista de documentos crudos extraídos.
    """
    ext = os.path.splitext(file_path)[1].lower()
    
    # Seleccionar el loader adecuado
    if ext == '.pdf':
        loader = PyPDFLoader(file_path)
    elif ext in ['.doc', '.docx']:
        loader = Docx2txtLoader(file_path)
    elif ext == '.txt':
        loader = TextLoader(file_path, encoding='utf-8')
    else:
        raise ValueError(f"Formato de archivo no soportado: {ext}")
        
    documents = loader.load()
    return documents

def build_vectorstore(documents):
    """
    Divide los documentos en fragmentos (chunks), genera sus embeddings
    usando sentence-transformers y los persiste en ChromaDB.
    """
    # 1. Instanciar el modelo de embeddings local (Offline)
    embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    
    # 2. Dividir documentos en pedazos para optimizar la ventana de contexto
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=150)
    chunks = text_splitter.split_documents(documents)
    
    # 3. Crear o agregar a la base de datos vectorial Chroma existente
    vectorstore = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=settings.CHROMA_PERSIST_DIR,
        collection_name=settings.CHROMA_COLLECTION_NAME
    )
    
    # 4. Asegurarse de que los datos vectores queden guardados en disco
    if hasattr(vectorstore, 'persist'):
        vectorstore.persist()
        
    return vectorstore

def rag_query(pregunta):
    """
    Ejecuta el proceso RAG completo:
    1. Carga ChromaDB.
    2. Busca documentos similares usando retriever.
    3. Llama a Ollama (llm) con el contexto recuperado.
    4. Devuelve la respuesta y las fuentes utilizadas.
    """
    # Obtener LLM y Embeddings locales
    llm = get_llm()
    embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    
    # Cargar la base vectorial persistente
    vectorstore = Chroma(
        persist_directory=settings.CHROMA_PERSIST_DIR,
        collection_name=settings.CHROMA_COLLECTION_NAME,
        embedding_function=embeddings
    )
    
    # Configurar el recuperador para obtener los 4 pedazos más relevantes
    retriever = vectorstore.as_retriever(search_kwargs={"k": 4})
    
    # Cadena que hace interactuar al Retriever y al LLM
    qa_chain = RetrievalQA.from_chain_type(
        llm=llm,
        chain_type="stuff",
        retriever=retriever,
        return_source_documents=True
    )
    
    # Procesar la consulta de QA
    response = qa_chain.invoke({"query": pregunta})
    
    answer = response.get('result', '')
    source_docs = response.get('source_documents', [])
    
    # Extraer las fuentes únicas de los metadatos y depurar la lista
    fuentes = []
    for doc in source_docs:
        source_name = doc.metadata.get('source_file', 'Desconocido')
        fuentes.append(source_name)
    fuentes = list(set(fuentes))
    
    return {
        'answer': answer,
        'sources': fuentes
    }
