pipeline {
    agent any

    environment {
        DOCKER_IMAGE = "devsecops-app"
        DOCKER_TAG   = "${BUILD_NUMBER}"
        APP_PORT     = "5000"
    }

    stages {
        stage('SAST & SCA') {
            steps {
                echo 'Analyse du code avec Bandit et Safety...'
                sh '''
                    docker run --rm -v "${WORKSPACE}":/app python:3.12-slim bash -c "
                        pip install bandit safety &&
                        bandit -r /app -f json -o /app/bandit-report.json || true &&
                        bandit -r /app -f html -o /app/bandit-report.html || true
                    "
                '''
            }
        }

        stage('Secrets Scanning') {
            steps {
                sh '''
                    docker run --rm -v "${WORKSPACE}":/path zricethezav/gitleaks:latest \
                        detect --source="/path" --report-format=json \
                        --report-path=/path/gitleaks-report.json --no-git || true
                '''
            }
        }

        stage('Build Docker Image') {
            steps {
                sh '''
                    cd "${WORKSPACE}"
                    docker build -t ${DOCKER_IMAGE}:${DOCKER_TAG} .
                    docker tag ${DOCKER_IMAGE}:${DOCKER_TAG} ${DOCKER_IMAGE}:latest
                '''
            }
        }

        stage('Docker Security Scan') {
            steps {
                sh '''
                    docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
                        aquasec/trivy:latest image ${DOCKER_IMAGE}:${DOCKER_TAG} || true
                '''
            }
        }

        stage('Deploy to Staging') {
            steps {
                sh '''
                    docker stop devsecops-staging 2>/dev/null || true
                    docker rm devsecops-staging 2>/dev/null || true
                    docker run -d --name devsecops-staging --network jenkins \
                        -p ${APP_PORT}:5000 ${DOCKER_IMAGE}:${DOCKER_TAG}
                    sleep 10
                '''
            }
        }

        stage('DAST') {
            steps {
                sh '''
                    docker run --rm --network jenkins \
                        owasp/zap2docker-stable zap-baseline.py \
                        -t http://devsecops-staging:5000 || true
                '''
            }
        }
    }

    post {
        always {
            archiveArtifacts artifacts: '*-report.*', allowEmptyArchive: true
        }
    }
}
