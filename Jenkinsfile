pipeline {
agent any

```
environment {
    DOCKER_IMAGE = "devsecops-app"
    DOCKER_TAG   = "${BUILD_NUMBER}"
    APP_PORT     = "5000"
    
    // Absolute paths for pipx-installed tools
    BANDIT      = "/home/viper/.local/bin/bandit"
    SAFETY      = "/home/viper/.local/bin/safety"
    
    // Docker binary path (adjust if docker is elsewhere)
    DOCKER_BIN  = "/usr/bin/docker"
}

stages {
    stage('Checkout') {
        steps {
            echo 'Récupération du code source...'
            checkout scm
        }
    }
    
    stage('SAST & SCA') {
        steps {
            echo 'Analyse du code avec Bandit et Safety...'
            sh '''
                ${BANDIT} -r . -f json -o bandit-report.json || true
                ${BANDIT} -r . -f html -o bandit-report.html || true
                ${SAFETY} check --json --output safety-report.json || true
                ${SAFETY} check || true
                echo "Rapports Bandit et Safety générés"
            '''
        }
    }
    
    stage('Secrets Scanning') {
        steps {
            echo 'Recherche de secrets exposés avec Gitleaks...'
            sh '''
                ${DOCKER_BIN} pull zricethezav/gitleaks:latest
                ${DOCKER_BIN} run --rm -v $(pwd):/path zricethezav/gitleaks:latest \
                    detect --source="/path" \
                    --report-format=json \
                    --report-path=/path/gitleaks-report.json \
                    --no-git || echo "Secrets détectés (attendu pour la démo)"
            '''
        }
    }
    
    stage('Build Docker Image') {
        steps {
            echo "Construction de l'image Docker..."
            sh '''
                ${DOCKER_BIN} build -t ${DOCKER_IMAGE}:${DOCKER_TAG} .
                ${DOCKER_BIN} tag ${DOCKER_IMAGE}:${DOCKER_TAG} ${DOCKER_IMAGE}:latest
                echo "Image créée: ${DOCKER_IMAGE}:${DOCKER_TAG}"
            '''
        }
    }
    
    stage('Docker Security Scan') {
        steps {
            echo "Scan de sécurité de l'image avec Trivy..."
            sh '''
                ${DOCKER_BIN} pull aquasec/trivy:latest
                ${DOCKER_BIN} run --rm \
                    -v /var/run/docker.sock:/var/run/docker.sock \
                    -v $(pwd):/output \
                    aquasec/trivy:latest image \
                    --format json \
                    --output /output/trivy-report.json \
                    ${DOCKER_IMAGE}:${DOCKER_TAG} || true
                
                ${DOCKER_BIN} run --rm \
                    -v /var/run/docker.sock:/var/run/docker.sock \
                    aquasec/trivy:latest image \
                    --severity HIGH,CRITICAL \
                    ${DOCKER_IMAGE}:${DOCKER_TAG} || true
            '''
        }
    }
    
    stage('Deploy to Staging') {
        steps {
            echo 'Déploiement en environnement de test...'
            sh '''
                ${DOCKER_BIN} stop devsecops-staging 2>/dev/null || true
                ${DOCKER_BIN} rm devsecops-staging 2>/dev/null || true
                
                ${DOCKER_BIN} run -d \
                    --name devsecops-staging \
                    --network jenkins \
                    -p ${APP_PORT}:5000 \
                    ${DOCKER_IMAGE}:${DOCKER_TAG}
                
                sleep 10
                curl -f http://localhost:${APP_PORT} || exit 1
                echo "Application déployée sur http://localhost:${APP_PORT}"
            '''
        }
    }
    
    stage('DAST - Tests dynamiques') {
        steps {
            echo "Scan dynamique avec OWASP ZAP..."
            sh '''
                ${DOCKER_BIN} pull owasp/zap2docker-stable
                
                ${DOCKER_BIN} run --rm \
                    --network jenkins \
                    -v $(pwd):/zap/wrk:rw \
                    owasp/zap2docker-stable \
                    zap-baseline.py \
                    -t http://devsecops-staging:5000 \
                    -J zap-report.json \
                    -r zap-report.html || echo "Vulnérabilités détectées (attendu)"
            '''
        }
    }
    
    stage('Security Gate') {
        steps {
            echo '''
```

═══════════════════════════════════════
RÉSUMÉ DES CONTRÔLES DE SÉCURITÉ
═══════════════════════════════════════
✓ SAST (Bandit)     : Terminé
✓ SCA (Safety)      : Terminé
✓ Secrets (Gitleaks): Terminé
✓ Docker (Trivy)    : Terminé
✓ DAST (OWASP ZAP)  : Terminé
═══════════════════════════════════════
'''
}
}
}

```
post {
    always {
        echo 'Archivage des rapports...'
        archiveArtifacts artifacts: '*-report.*', allowEmptyArchive: true
        
        publishHTML(target: [
            allowMissing: true,
            alwaysLinkToLastBuild: true,
            keepAll: true,
            reportDir: '.',
            reportFiles: 'bandit-report.html,zap-report.html',
            reportName: 'Security Reports'
        ])
    }
}
```

}

