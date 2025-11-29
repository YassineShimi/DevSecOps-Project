#  GUIDE POUR DÉVELOPPEURS

## CE QUE TU DOIS FAIRE SUR TON ORDINATEUR

### 1. Installer VS Code (si pas déjà fait)
- Télécharger ici: https://code.visualstudio.com/

### 2. Installer ces extensions dans VS Code:
- **SonarLint** → Trouve les problèmes de sécurité
- **GitLens** → Voir l historique du code
- **Python** → Pour le code Python

### 3. Comment installer une extension:
1. Ouvrir VS Code
2. Cliquer sur l icône des extensions à gauche
3. Rechercher "SonarLint"
4. Cliquer sur "Install"

### 4. Vérifications avant d'envoyer ton code:
```bash
# Scanner le code pour les problèmes
docker run --rm -v $(pwd):/app python:3.9 bandit -r /app

# Vérifier les mots de passe exposés
docker run --rm -v $(pwd):/path zricethezav/gitleaks detect --source=/path --no-git
