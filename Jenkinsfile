pipeline {
    agent any

    environment {
        DOCKER_IMAGE = "devsecops-app"
        DOCKER_TAG   = "${BUILD_NUMBER}"
        APP_PORT     = "5000"
        EMAIL_TO     = "vipertn2@gmail.com"
    }

    options {
        timestamps()
        disableConcurrentBuilds()
    }

    stages {
        stage('Checkout') {
            steps {
                echo "Récupération du code source"
                checkout scm
            }
        }

        stage('SAST - Bandit') {
            steps {
                echo "Analyse statique avec Bandit"
                sh '''
                    docker run --rm -v "${WORKSPACE}":/app -w /app python:3.12-slim bash -c "
                        pip install --no-cache-dir bandit >/dev/null 2>&1 && \
                        bandit -r /app -f json -o /app/bandit-report.json || true
                    "
                '''
            }
            post {
                always {
                    script {
                        if (fileExists('bandit-report.json')) {
                            def report = readJSON file: 'bandit-report.json'
                            def issues = (report.results ?: []).size()
                            if (issues > 0) {
                                error "Bandit a détecté ${issues} vulnérabilités. Arrêt du pipeline."
                            }
                        }
                    }
                }
            }
        }

        stage('SCA - Safety') {
            steps {
                echo "Analyse des dépendances avec Safety"
                sh '''
                    docker run --rm -v "${WORKSPACE}":/src python:3.12-slim bash -c "
                        pip install --no-cache-dir safety >/dev/null 2>&1 && \
                        safety scan --json > /src/safety-report.json || true
                    "
                '''
            }
            post {
                always {
                    script {
                        if (fileExists('safety-report.json')) {
                            def data = readJSON file: 'safety-report.json'
                            def vulns = data.vulnerabilities ?: []
                            if (vulns.size() > 0) {
                                error "Safety a détecté des vulnérabilités. Arrêt du pipeline."
                            }
                        }
                    }
                }
            }
        }

        stage('Secrets - Gitleaks') {
            steps {
                echo "Scan des secrets avec Gitleaks"
                sh '''
                    docker run --rm -v "${WORKSPACE}":/src zricethezav/gitleaks detect \
                        --source=/src --report-path=/src/gitleaks-report.json --report-format=json || true
                '''
            }
            post {
                always {
                    script {
                        if (fileExists('gitleaks-report.json')) {
                            def gl = readJSON file: 'gitleaks-report.json'
                            def findings = gl.findings ?: []
                            if (findings.size() > 0) {
                                error "Gitleaks a détecté ${findings.size()} secrets exposés. Arrêt du pipeline."
                            }
                        }
                    }
                }
            }
        }

        stage('Build Docker Image') {
            steps {
                echo "Construction de l'image Docker"
                sh """
                    docker build -t ${DOCKER_IMAGE}:${DOCKER_TAG} .
                    docker tag ${DOCKER_IMAGE}:${DOCKER_TAG} ${DOCKER_IMAGE}:latest
                """
            }
        }

        stage('Docker Scan - Trivy') {
            steps {
                echo "Scan d'image Docker avec Trivy (CRITICAL/HIGH)"
                sh '''
                    docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
                        -v "${WORKSPACE}":/output aquasec/trivy:latest image \
                        --severity CRITICAL,HIGH --format json --output /output/trivy-report.json \
                        ${DOCKER_IMAGE}:${DOCKER_TAG} || true
                '''
            }
            post {
                always {
                    script {
                        if (fileExists('trivy-report.json')) {
                            def trivy = readJSON file: 'trivy-report.json'
                            def results = trivy.Results ?: []
                            def criticals = 0
                            for (res in results) {
                                def vuls = res.Vulnerabilities ?: []
                                for (v in vuls) {
                                    if (v.Severity == 'CRITICAL' || v.Severity == 'HIGH') {
                                        criticals++
                                    }
                                }
                            }
                            if (criticals > 0) {
                                error "Trivy a détecté ${criticals} vulnérabilités HIGH/CRITICAL. Arrêt du pipeline."
                            }
                        }
                    }
                }
            }
        }

        stage('Deploy to Staging') {
            steps {
                echo "Déploiement en staging (conteneur)"
                sh '''
                    docker stop devsecops-staging 2>/dev/null || true
                    docker rm devsecops-staging 2>/dev/null || true
                    docker run -d --name devsecops-staging --network jenkins \
                        -p ${APP_PORT}:5000 ${DOCKER_IMAGE}:${DOCKER_TAG}
                    sleep 8
                '''
            }
        }

        stage('DAST - OWASP ZAP') {
            steps {
                echo "DAST: exécution OWASP ZAP scan"
                sh '''
                    docker run --rm --network jenkins -v "${WORKSPACE}":/zap/wrk:rw \
                        ghcr.io/zaproxy/zaproxy:stable zap-baseline.py \
                        -t http://devsecops-staging:5000 -J /zap/wrk/zap-report.json -r /zap/wrk/zap-report.html || true
                '''
            }
            post {
                always {
                    script {
                        if (fileExists('zap-report.json')) {
                            def zap = readJSON file: 'zap-report.json'
                            def sites = zap.site ?: []
                            def highAlerts = 0
                            for (s in sites) {
                                def alerts = s.alerts ?: []
                                for (a in alerts) {
                                    // riskcode: 3 usually corresponds to High
                                    if (a.riskcode == '3' || a.risk == 'High') {
                                        highAlerts++
                                    }
                                }
                            }
                            if (highAlerts > 0) {
                                error "ZAP a détecté ${highAlerts} alertes HIGH. Arrêt du pipeline."
                            }
                        }
                    }
                }
            }
        }

        stage('Generate Final Report') {
            steps {
                echo "Génération du rapport final HTML"
                sh '''
                    cat > security-report.html <<'EOF'
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>Security Report</title></head>
<body>
<h1>Rapport de Sécurité - Build ${BUILD_NUMBER}</h1>
<ul>
<li><a href="bandit-report.json">SAST - Bandit (JSON)</a></li>
<li><a href="safety-report.json">SCA - Safety (JSON)</a></li>
<li><a href="gitleaks-report.json">Secrets - Gitleaks (JSON)</a></li>
<li><a href="trivy-report.json">Docker - Trivy (JSON)</a></li>
<li><a href="zap-report.html">DAST - ZAP (HTML)</a></li>
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
            echo "Archivage des rapports"
            // archive artifacts; if plugin requires allowEmptyArchive true to not fail when no file, adjust
            archiveArtifacts artifacts: 'bandit-report.json, safety-report.json, gitleaks-report.json, trivy-report.json, zap-report.json, zap-report.html, security-report.html', allowEmptyArchive: true, fingerprint: true

            publishHTML([
                reportDir: '.',
                reportFiles: 'security-report.html',
                reportName: 'Security Dashboard',
                keepAll: true,
                allowMissing: true,
                alwaysLinkToLastBuild: false,
                alwaysLinkToLastSuccessfulBuild: false
            ])
        }

        failure {
            echo "Envoi email - échec du pipeline"
            mail to: "${EMAIL_TO}",
                 subject: "DevSecOps Pipeline FAILED - Build #${env.BUILD_NUMBER}",
                 body: "Le pipeline a échoué suite à la détection d'une vulnérabilité ou une erreur. Voir les rapports dans les artifacts."
        }

        success {
            echo "Pipeline réussi - envoi email"
            mail to: "${EMAIL_TO}",
                 subject: "DevSecOps Pipeline SUCCESS - Build #${env.BUILD_NUMBER}",
                 body: "Tous les contrôles ont été validés sans vulnérabilités. Build #${env.BUILD_NUMBER}"
        }
    }
}

