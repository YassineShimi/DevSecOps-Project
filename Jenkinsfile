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
                echo "Checkout"
                checkout scm
            }
        }

        stage('SAST - Bandit') {
            steps {
                echo "Run Bandit (SAST)"
                sh '''
                    docker run --rm -v "${WORKSPACE}":/app -w /app python:3.12-slim bash -c "
                        pip install --no-cache-dir bandit >/dev/null 2>&1 || true
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
                                error "Bandit detected ${issues} findings -> stop pipeline."
                            }
                        }
                    }
                }
            }
        }

        stage('SCA - Safety') {
            steps {
                echo "Run Safety (SCA)"
                sh '''
                    docker run --rm -v "${WORKSPACE}":/src python:3.12-slim bash -c "
                        pip install --no-cache-dir safety >/dev/null 2>&1 || true
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
                                error "Safety found ${vulns.size()} vulnerabilities -> stop pipeline."
                            }
                        }
                    }
                }
            }
        }

        stage('Secrets - Gitleaks') {
            steps {
                echo "Run Gitleaks (Secrets scan)"
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
                                error "Gitleaks found ${findings.size()} secrets -> stop pipeline."
                            }
                        }
                    }
                }
            }
        }

        stage('Build Docker Image') {
            steps {
                echo "Build Docker image"
                sh """
                    docker build -t ${DOCKER_IMAGE}:${DOCKER_TAG} .
                    docker tag ${DOCKER_IMAGE}:${DOCKER_TAG} ${DOCKER_IMAGE}:latest || true
                """
            }
        }

        stage('Docker Scan - Trivy') {
            steps {
                echo "Run Trivy on built image (HIGH/CRITICAL)"
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
                                error "Trivy found ${criticals} HIGH/CRITICAL vulnerabilities -> stop pipeline."
                            }
                        }
                    }
                }
            }
        }

        stage('Deploy to Staging') {
            steps {
                echo "Deploy container to staging"
                sh '''
                    docker stop devsecops-staging 2>/dev/null || true
                    docker rm devsecops-staging 2>/dev/null || true
                    docker run -d --name devsecops-staging --network jenkins -p ${APP_PORT}:5000 ${DOCKER_IMAGE}:${DOCKER_TAG} || true
                    sleep 8
                '''
            }
        }

        stage('DAST - OWASP ZAP') {
            steps {
                echo "Run OWASP ZAP baseline scan"
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
                                    if ((a.riskcode == '3') || (a.risk =~ /(?i)high/)) {
                                        highAlerts++
                                    }
                                }
                            }
                            if (highAlerts > 0) {
                                error "ZAP found ${highAlerts} HIGH alerts -> stop pipeline."
                            }
                        }
                    }
                }
            }
        }

        stage('Collect Reports') {
            steps {
                echo "Ensure reports exist (collected)"
                sh '''
                    # touch fallback files if missing so archiveArtifacts won't fail
                    [ -f bandit-report.json ] || echo '{}' > bandit-report.json
                    [ -f safety-report.json ] || echo '{"vulnerabilities": []}' > safety-report.json
                    [ -f gitleaks-report.json ] || echo '{"findings": []}' > gitleaks-report.json
                    [ -f trivy-report.json ] || echo '{"Results": []}' > trivy-report.json
                    [ -f zap-report.json ] || echo '{"site": []}' > zap-report.json
                    [ -f zap-report.html ] || echo '<html><body><h1>ZAP report</h1></body></html>' > zap-report.html
                '''
            }
        }
    }

    post {
        always {
            echo "Archive artifacts (no HTML publishing)"
            archiveArtifacts artifacts: 'bandit-report.json, safety-report.json, gitleaks-report.json, trivy-report.json, zap-report.json, zap-report.html', allowEmptyArchive: true, fingerprint: true
        }

        failure {
            echo "Pipeline failed - sending notification (requires SMTP configured)"
            mail to: "${EMAIL_TO}",
                 subject: "DevSecOps Pipeline FAILED - Build #${env.BUILD_NUMBER}",
                 body: "Le pipeline a échoué. Consultez les artifacts pour les rapports."
        }

        success {
            echo "Pipeline succeeded - sending notification (requires SMTP configured)"
            mail to: "${EMAIL_TO}",
                 subject: "DevSecOps Pipeline SUCCESS - Build #${env.BUILD_NUMBER}",
                 body: "Tous les contrôles sont passés. Build #${env.BUILD_NUMBER}"
        }
    }
}

