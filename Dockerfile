FROM python:3.9-slim

WORKDIR /app

# Mise à jour du système et installation des dépendances système
RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y --no-install-recommends \
    curl \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Copier les dépendances Python d'abord pour meilleur caching
COPY requirements.txt .

# Installer les dépendances Python
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copier le code de l'application
COPY app.py .

# Créer un utilisateur non-root pour la sécurité
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app

USER appuser

# Exposer le port
EXPOSE 5000

# Variables d'environnement pour la sécurité
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Démarrer l'application
CMD ["python3", "app.py"]
