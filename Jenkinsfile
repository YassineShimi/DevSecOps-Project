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
                script {
                    sh '''
                        docker run --rm \
                            -v "${WORKSPACE}":/app \
                            -w /app \
                            python:3.12-slim \
                            bash -c "pip install bandit safety && \
                                bandit -r /app -f json -o /app/bandit-report.json || true && \
                                bandit -r /app -f html -o /app/bandit-report.html || true && \
                                safety check --json --output /app/safety-report.json || true && \
                                safety check || true"
                    '''
                }
            }
        }

        stage('Secrets Scanning') {
            steps {
                script {
                    sh '''
                        docker run --rm \
                            -v "${WORKSPACE}":/path \
                            zricethezav/gitleaks:latest \
                            detect --source="/path" \
                            --report-format=json \
                            --report-path=/path/gitleaks-report.json \
                            --no-git || echo "Secrets détectés"
                    '''
                }
            }
        }

        stage('Build Docker Image') {
            steps {
                script {
                    sh '''
                        docker build -t ${DOCKER_IMAGE}:${DOCKER_TAG} .
                        docker tag ${DOCKER_IMAGE}:${DOCKER_TAG} ${DOCKER_IMAGE}:latest
                    '''
                }
            }
        }

        stage('Docker Security Scan') {
            steps {
                script {
                    sh '''
                        docker run --rm \
                            -v /var/run/docker.sock:/var/run/docker.sock \
                            -v "${WORKSPACE}":/output \
                            aquasec/trivy:latest image \
                            --format json \
                            --output /output/trivy-report.json \
                            ${DOCKER_IMAGE}:${DOCKER_TAG} || true
                    '''
                }
            }
        }

        stage('Deploy to Staging') {
            steps {
                script {
                    sh '''
                        docker stop devsecops-staging 2>/dev/null || true
                        docker rm devsecops-staging 2>/dev/null || true
                        docker run -d \
                            --name devsecops-staging \
                            --network jenkins \
                            -p ${APP_PORT}:5000 \
                            ${DOCKER_IMAGE}:${DOCKER_TAG}
                        sleep 10
                    '''
                }
            }
        }

        stage('DAST - Tests dynamiques') {
            steps {
                script {
                    sh '''
                        docker run --rm \
                            --network jenkins \
                            -v "${WORKSPACE}":/zap/wrk:rw \
                            owasp/zap2docker-stable \
                            zap-baseline.py \
                            -t http://devsecops-staging:5000 \
                            -J zap-report.json \
                            -r zap-report.html || echo "Vulnérabilités détectées"
                    '''
                }
            }
        }

        stage('Security Gate') {
            steps {
                echo '''
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
