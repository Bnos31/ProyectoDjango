import hashlib

def calculate_sha256(file):
    """Calcula el hash SHA-256 de un archivo subido en memoria/disco"""
    sha1 = hashlib.sha256()
    # Volver el cursor a cero por seguridad
    file.seek(0)
    for chunk in file.chunks():
        sha1.update(chunk)
    # Volver el cursor a cero para que Django lo pueda guardar luego
    file.seek(0)
    return sha1.hexdigest()
