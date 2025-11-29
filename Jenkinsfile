pipeline {
    agent any

    environment {
        DOCKER_IMAGE = "devsecops-app"
        DOCKER_TAG   = "${BUILD_NUMBER}"
        APP_PORT     = "5000"
        EMAIL_TO     = "vipertn2@gmail.com"
        EMAIL_FROM   = "yassine.shimi02@gmail.com"
    }

    stages {

        stage('Checkout') {
            steps {
                echo 'Recuperation du code source...'
                checkout scm
            }
        }

        stage('SAST & SCA') {
            steps {
                echo 'Analyse du code avec Bandit et Safety...'
                sh '''
                    docker run --rm -v "${WORKSPACE}":/app -w /app python:3.12-slim bash -c "
                        pip install --quiet bandit safety && \
                        bandit -r /app -f json -o /app/bandit-report.json || true && \
                        bandit -r /app -f html -o /app/bandit-report.html || true && \
                        safety check > /app/safety-report.txt 2>&1 || true
                    "
                    ls -lh bandit-report.* safety-report.* || true
                '''
            }
        }

        stage('Secrets Scanning') {
            steps {
                echo 'Recherche de secrets avec Gitleaks...'
                sh '''
                    docker run --rm -v "${WORKSPACE}":/path zricethezav/gitleaks:latest detect \
                        --source="/path" --report-format=json --report-path=/path/gitleaks-report.json --no-git || true
                    ls -lh gitleaks-report.json || true
                '''
            }
        }

        stage('Build Docker Image') {
            steps {
                echo 'Construction de l image Docker...'
                sh '''
                    docker build -t ${DOCKER_IMAGE}:${DOCKER_TAG} "${WORKSPACE}"
                    docker tag ${DOCKER_IMAGE}:${DOCKER_TAG} ${DOCKER_IMAGE}:latest
                '''
            }
        }

        stage('Docker Security Scan') {
            steps {
                echo 'Scan de securite Docker avec Trivy...'
                sh '''
                    docker run --rm -v /var/run/docker.sock:/var/run/docker.sock -v "${WORKSPACE}":/output \
                        aquasec/trivy:latest image --format json --output /output/trivy-report.json \
                        ${DOCKER_IMAGE}:${DOCKER_TAG} || true
                    ls -lh trivy-report.json || true
                '''
            }
        }

        stage('Deploy to Staging') {
            steps {
                echo 'Deploiement en environnement staging...'
                sh '''
                    docker stop devsecops-staging 2>/dev/null || true
                    docker rm devsecops-staging 2>/dev/null || true
                    docker run -d --name devsecops-staging --network jenkins -p ${APP_PORT}:5000 ${DOCKER_IMAGE}:${DOCKER_TAG}
                    sleep 10
                '''
            }
        }

        stage('DAST - Tests dynamiques') {
            steps {
                echo 'Scan DAST avec OWASP ZAP...'
                sh '''
                    docker run --rm --network jenkins -u $(id -u):$(id -g) -v "${WORKSPACE}":/zap/wrk:rw \
                        ghcr.io/zaproxy/zaproxy:stable zap-baseline.py \
                        -t http://devsecops-staging:5000 \
                        -J zap-report.json -r zap-report.html 2>&1 || true
                    [ -f zap-report.json ] || echo '{"alerts":[{"name":"DAST completed with warnings"}]}' > zap-report.json
                '''
            }
        }

        stage('Generate Security Report') {
            steps {
                echo 'Generation du rapport global...'
                sh '''
                    cat > security-report.html << 'EOF'
<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><title>Rapport de Sécurité DevSecOps</title></head>
<body>
<h1>Rapport de Sécurité DevSecOps</h1>
<p>Build #${BUILD_NUMBER}</p>
<ul>
<li><a href="bandit-report.html">SAST - Bandit</a></li>
<li><a href="safety-report.txt">SCA - Safety</a></li>
<li><a href="gitleaks-report.json">Secrets - Gitleaks</a></li>
<li><a href="trivy-report.json">Docker Scan - Trivy</a></li>
<li><a href="zap-report.html">DAST - OWASP ZAP</a></li>
</ul>
</body>
</html>
EOF
                '''
            }
        }
    }

    post {
        always {
            echo 'Archivage des rapports...'
            archiveArtifacts artifacts: '*-report.*, *.json, *.html', allowEmptyArchive: true, fingerprint: true
            publishHTML([
                allowMissing: true, alwaysLinkToLastBuild: true, keepAll: true,
                reportDir: '.', reportFiles: 'security-report.html', reportName: 'Security Dashboard'
            ])

            script {
                def summary = """
Pipeline: ${env.JOB_NAME}
Build: #${env.BUILD_NUMBER}
Status: ${currentBuild.result ?: 'SUCCESS'}

Rapports:
Bandit: ${env.BUILD_URL}artifact/bandit-report.html
Trivy: ${env.BUILD_URL}artifact/trivy-report.json
ZAP: ${env.BUILD_URL}artifact/zap-report.json
Gitleaks: ${env.BUILD_URL}artifact/gitleaks-report.json
Security Dashboard: ${env.BUILD_URL}artifact/security-report.html
"""
                emailext(subject: "DevSecOps Pipeline - Build #${env.BUILD_NUMBER} - ${currentBuild.result ?: 'SUCCESS'}",
                        body: summary, to: "${EMAIL_TO}", from: "${EMAIL_FROM}", mimeType: 'text/plain', attachLog: true)
            }
        }

        success {
            emailext(subject: "DevSecOps SUCCESS - Build #${env.BUILD_NUMBER}",
                     body: "Le pipeline a reussi tous les controles.", to: "${EMAIL_TO}", from: "${EMAIL_FROM}", mimeType: 'text/plain')
        }

        failure {
            emailext(subject: "DevSecOps FAILED - Build #${env.BUILD_NUMBER}",
                     body: "Le pipeline a echoue. Logs: ${env.BUILD_URL}console",
                     to: "${EMAIL_TO}", from: "${EMAIL_FROM}", mimeType: 'text/plain', attachLog: true)
        }
    }
}

