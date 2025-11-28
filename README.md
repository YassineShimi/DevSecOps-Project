# 🔒 Projet DevSecOps - Pipeline CI/CD Sécurisé

## 📌 Description
Pipeline Jenkins intégrant la sécurité à chaque étape du développement.

## 🛠️ Technologies utilisées
- **Jenkins** : Orchestration CI/CD
- **Docker** : Conteneurisation
- **Bandit** : SAST (Python)
- **Safety** : SCA (dépendances Python)
- **Gitleaks** : Détection de secrets
- **Trivy** : Scan de sécurité Docker
- **OWASP ZAP** : DAST (tests dynamiques)

## 📊 Architecture du Pipeline
```
┌─────────────┐
│   Checkout  │
└──────┬──────┘
       │
┌──────▼──────┐
│  SAST & SCA │ ← Bandit + Safety
└──────┬──────┘
       │
┌──────▼──────┐
│   Secrets   │ ← Gitleaks
└──────┬──────┘
       │
┌──────▼──────┐
│    Build    │ ← Docker build
└──────┬──────┘
       │
┌──────▼──────┐
│ Docker Scan │ ← Trivy
└──────┬──────┘
       │
┌──────▼──────┐
│   Deploy    │ ← Staging
└──────┬──────┘
       │
┌──────▼──────┐
│    DAST     │ ← OWASP ZAP
└──────┬──────┘
       │
┌──────▼──────┐
│Security Gate│
└─────────────┘
```

## 🚀 Installation

### Prérequis
```bash
# Docker
docker --version

# Jenkins (via Docker)
docker run -d \
  --name jenkins \
  --network jenkins \
  -p 8080:8080 \
  -p 50000:50000 \
  -v jenkins_home:/var/jenkins_home \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -u root \
  jenkins/jenkins:lts-jdk17

# Installer Docker dans Jenkins
docker exec -u root jenkins apt-get update
docker exec -u root jenkins apt-get install -y docker.io

# Pull des images nécessaires
docker pull python:3.12-slim
docker pull zricethezav/gitleaks:latest
docker pull aquasec/trivy:latest
docker pull ghcr.io/zaproxy/zaproxy:stable
```

## 📦 Utilisation

### 1. Créer le job Jenkins
1. Ouvrir Jenkins : http://localhost:8080
2. New Item → Pipeline
3. Configuration :
   - Repository URL : `https://github.com/YassineShimi/DevSecOps-Project.git`
   - Script Path : `Jenkinsfile`

### 2. Lancer le build
```
Build Now
```

### 3. Consulter les rapports
- Jenkins → Job → Build #N → Security Reports

## 📄 Rapports générés

| Rapport | Outil | Format |
|---------|-------|--------|
| bandit-report.html | Bandit | HTML |
| bandit-report.json | Bandit | JSON |
| safety-report.json | Safety | JSON |
| gitleaks-report.json | Gitleaks | JSON |
| trivy-report.json | Trivy | JSON |
| zap-report.html | OWASP ZAP | HTML |
| zap-report.json | OWASP ZAP | JSON |

## 🔍 Vulnérabilités détectées

### Code (SAST)
- XSS (Cross-Site Scripting)
- Injection SQL
- Secrets hardcodés

### Dépendances (SCA)
- Flask 2.3.0 : CVE-2023-30861 (HIGH)
- Werkzeug 2.3.0 : 4 CVE (HIGH/MEDIUM)

### Docker
- 59 vulnérabilités (MEDIUM/LOW)

## 🎯 Résultats

✅ Pipeline fonctionnel à 100%  
✅ Tous les contrôles de sécurité automatisés  
✅ Rapports générés et archivés  
✅ Application déployée en staging  
✅ Tests dynamiques effectués

## 📞 Contact
**Auteur :** Yassine Shimi  
**Date :** Novembre 2025
