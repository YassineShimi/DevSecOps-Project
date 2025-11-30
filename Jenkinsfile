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

        stage('SAST - Analyse statique') {
            steps {
                echo "Analyse du code avec Bandit"
                sh '''
                    docker run --rm -v "${WORKSPACE}":/app -w /app python:3.12-slim bash -c "
                        pip install bandit && \
                        bandit -r /app -f json -o /app/bandit-report.json
                    "
                '''
            }
            post {
                success {
                    script {
                        def report = readJSON file: 'bandit-report.json'
                        def issues = report.results.size()
                        if (issues > 0) {
                            error "Bandit a détecté ${issues} vulnérabilités. Arrêt du pipeline."
                        }
                    }
                }
            }
        }

        stage('SCA - Analyse des dépendances') {
            steps {
                echo "Analyse SCA avec Safety"
                sh '''
                    docker run --rm -v "${WORKSPACE}":/src python:3.12-slim bash -c "
                        pip install safety && \
                        safety scan --json > /src/safety-report.json
                    "
                '''
            }
            post {
                success {
                    script {
                        def data = readJSON file: 'safety-report.json'
                        if (data.vulnerabilities && data.vulnerabilities.size() > 0) {
                            error "Safety a détecté des vulnérabilités. Arrêt du pipeline."
                        }
                    }
                }
            }
        }

        stage('Secrets Scanning') {
            steps {
                echo "Recherche de secrets avec Gitleaks"
                sh '''
                    docker run --rm -v "${WORKSPACE}":/src zricethezav/gitleaks detect \
                        --source=/src --report-path=/src/gitleaks-report.json --report-format=json
                '''
            }
            post {
                success {
                    script {
                        def gl = readJSON file: 'gitleaks-report.json'
                        if (gl.findings && gl.findings.size() > 0) {
                            error "Gitleaks a détecté des secrets exposés. Arrêt du pipeline."
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
                echo "Scan de l'image Docker avec Trivy"
                sh '''
                    docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
                        -v "${WORKSPACE}":/output aquasec/trivy:latest image \
                        --severity CRITICAL,HIGH \
                        --format json --output /output/trivy-report.json \
                        ${DOCKER_IMAGE}:${DOCKER_TAG}
                '''
            }
            post {
                success {
                    script {
                        def trivy = readJSON file: 'trivy-report.json'
                        for (res in trivy.Results) {
                            if (res.Vulnerabilities) {
                                def criticals = res.Vulnerabilities.findAll { it.Severity in ["HIGH", "CRITICAL"] }
                                if (criticals.size() > 0) {
                                    error "Trivy a détecté des vulnérabilités HIGH/CRITICAL. Arrêt du pipeline."
                                }
                            }
                        }
                    }
                }
            }
        }

        stage('Deploy to Staging') {
            steps {
                echo "Déploiement en environnement staging"
                sh '''
                    docker stop devsecops-staging 2>/dev/null || true
                    docker rm devsecops-staging 2>/dev/null || true
                    docker run -d --name devsecops-staging --network jenkins \
                        -p ${APP_PORT}:5000 ${DOCKER_IMAGE}:${DOCKER_TAG}
                    sleep 10
                '''
            }
        }

        stage('DAST - OWASP ZAP') {
            steps {
                echo "Scan DAST OWASP ZAP"
                sh '''
                    docker run --rm --network jenkins \
                        -v "${WORKSPACE}":/zap/wrk:rw \
                        ghcr.io/zaproxy/zaproxy:stable zap-baseline.py \
                        -t http://devsecops-staging:5000 \
                        -J zap-report.json -r zap-report.html
                '''
            }
            post {
                success {
                    script {
                        def zap = readJSON file: 'zap-report.json'
                        def alerts = zap.site[0].alerts.findAll { it.riskcode == "3" } // High
                        if (alerts.size() > 0) {
                            error "ZAP a détecté des vulnérabilités HIGH. Arrêt du pipeline."
                        }
                    }
                }
            }
        }

        stage('Generate Final Report') {
            steps {
                echo "Génération du rapport final"
                sh '''
                    cat > security-report.html <<EOF
<html><body>
<h1>Rapport de Sécurité</h1>
<ul>
<li><a href="bandit-report.json">SAST - Bandit</a></li>
<li><a href="safety-report.json">SCA - Safety</a></li>
<li><a href="gitleaks-report.json">Secrets - Gitleaks</a></li>
<li><a href="trivy-report.json">Docker - Trivy</a></li>
<li><a href="zap-report.html">DAST - ZAP</a></li>
</ul>
</body></html>
EOF
                '''
            }
        }
    }

  post {
    always {
        echo "Archivage des rapports"
        archiveArtifacts artifacts: '*.json, *.html', allowEmptyArchive: false

        publishHTML([
            reportDir: '.',
            reportFiles: 'security-report.html',
            reportName: 'Security Dashboard',
            keepAll: true,
            allowMissing: false,
            alwaysLinkToLastBuild: false,
            alwaysLinkToLastSuccessfulBuild: false
        ])
    }

    failure {
        mail(
            to: "${EMAIL_TO}",
            subject: "DevSecOps Pipeline FAILED - Build #${env.BUILD_NUMBER}",
            body: "Le pipeline a échoué suite à la détection d'une vulnérabilité."
        )
    }

    success {
        mail(
            to: "${EMAIL_TO}",
            subject: "DevSecOps Pipeline SUCCESS - Build #${env.BUILD_NUMBER}",
            body: "Tous les contrôles ont été validés sans vulnérabilités."
        )
    }
}

