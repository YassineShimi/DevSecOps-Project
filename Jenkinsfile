pipeline {
    agent any

    environment {
        DOCKER_IMAGE = "devsecops-app"
        DOCKER_TAG   = "${BUILD_NUMBER}"
        APP_PORT     = "5000"
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
                    docker run --rm -v $(pwd):/app python:3.12-slim bash -c "
                        pip install bandit safety &&
                        bandit -r /app -f json -o /app/bandit-report.json || true &&
                        bandit -r /app -f html -o /app/bandit-report.html || true &&
                        safety check --json --output /app/safety-report.json || true &&
                        safety check || true
                    "
                    echo "Rapports Bandit et Safety générés"
                '''
            }
        }

        stage('Secrets Scanning') {
            steps {
                echo 'Recherche de secrets exposés avec Gitleaks...'
                sh '''
                    docker run --rm -v $(pwd):/path zricethezav/gitleaks:latest \
                        detect --source="/path" \
                        --report-format=json \
                        --report-path=/path/gitleaks-report.json \
                        --no-git || echo "Secrets détectés (attendu)"
                '''
            }
        }

        stage('Build Docker Image') {
            steps {
                echo "Construction de l'image Docker..."
                sh '''
                    docker build -t ${DOCKER_IMAGE}:${DOCKER_TAG} .
                    docker tag ${DOCKER_IMAGE}:${DOCKER_TAG} ${DOCKER_IMAGE}:latest
                    echo "Image créée: ${DOCKER_IMAGE}:${DOCKER_TAG}"
                '''
            }
        }

        stage('Docker Security Scan') {
            steps {
                echo "Scan de sécurité de l'image avec Trivy..."
                sh '''
                    docker run --rm aquasec/trivy:latest image \
                        --format json \
                        --output trivy-report.json \
                        ${DOCKER_IMAGE}:${DOCKER_TAG} || true
                '''
            }
        }

        stage('Deploy to Staging') {
            steps {
                echo 'Déploiement en environnement de test...'
                sh '''
                    docker stop devsecops-staging 2>/dev/null || true
                    docker rm devsecops-staging 2>/dev/null || true
                    docker run -d --name devsecops-staging -p ${APP_PORT}:5000 ${DOCKER_IMAGE}:${DOCKER_TAG}
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
                    docker run --rm --network host -v $(pwd):/zap/wrk:rw owasp/zap2docker-stable \
                        zap-baseline.py -t http://localhost:${APP_PORT} -J zap-report.json -r zap-report.html || echo "Vulnérabilités détectées (attendu)"
                '''
            }
        }

        stage('Security Gate') {
            steps {
                echo '''
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
}

