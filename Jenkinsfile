pipeline {
    agent any
    environment {
        DOCKER_IMAGE = "devsecops-app"
        DOCKER_TAG = "${BUILD_NUMBER}"
        APP_PORT = "5000"
        EMAIL_TO = "yass@entreprise.com"
        REPORT_DIR = "reports"
    }
    options {
        timestamps()
        buildDiscarder(logRotator(numToKeepStr: '10'))
    }
    stages {
        stage('Checkout') {
            steps {
                echo 'Recuperation du code source...'
                checkout scm
                sh 'mkdir -p reports'
            }
        }
        
        stage('SAST - Bandit Scan') {
            agent {
                docker {
                    image 'python:3.9-alpine'
                    args '-v $(pwd):/app -w /app'
                }
            }
            steps {
                echo 'Analyse statique avec Bandit...'
                sh '''
                    pip install bandit
                    bandit -r . -f html -o reports/bandit_report.html
                '''
            }
        }
        
        stage('SCA - Dependency Check') {
            steps {
                echo 'Analyse des dependances...'
                sh '''
                    docker run --rm -v $(pwd):/src owasp/dependency-check:latest \
                    --scan /src \
                    --format HTML \
                    --project "DevSecOps-Project" \
                    --out reports/dependency-check-report.html
                '''
            }
        }
        
        stage('Secrets Detection') {
            steps {
                echo 'Detection des secrets...'
                sh '''
                    docker run --rm -v $(pwd):/src zricethezav/gitleaks:latest \
                    detect -s /src -r reports/gitleaks_report.json
                '''
            }
        }
        
        stage('Build Docker Image') {
            steps {
                echo 'Construction image Docker...'
                sh "docker build -t ${DOCKER_IMAGE}:${DOCKER_TAG} ."
            }
        }
        
        stage('Docker Security Scan') {
            steps {
                echo 'Scan securite Docker...'
                sh '''
                    docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
                    -v $(pwd)/reports:/reports aquasec/trivy:latest \
                    image --format json -o /reports/trivy_report.json ${DOCKER_IMAGE}:${DOCKER_TAG}
                '''
            }
        }
        
        stage('Deploy to Staging') {
            steps {
                echo 'Deploiement en staging...'
                sh """
                    docker stop devsecops-app || true
                    docker rm devsecops-app || true
                    docker run -d -p ${APP_PORT}:5000 --name devsecops-app ${DOCKER_IMAGE}:${DOCKER_TAG}
                    sleep 10
                """
            }
        }
        
        stage('DAST - Dynamic Test') {
            steps {
                echo 'Test dynamique...'
                sh '''
                    docker run --rm -v $(pwd)/reports:/zap/wrk/:rw \
                    owasp/zap2docker-stable zap-baseline.py \
                    -t http://host.docker.internal:5000 \
                    -J reports/zap_report.json
                '''
            }
        }
    }
    post {
        always {
            echo 'Archivage des rapports...'
            sh 'docker stop devsecops-app || true'
            sh 'docker rm devsecops-app || true'
            archiveArtifacts artifacts: "reports/**", allowEmptyArchive: true
        }
        success {
            mail to: "${EMAIL_TO}",
                 subject: "SUCCESS - Build #${BUILD_NUMBER}",
                 body: "Build ${BUILD_NUMBER} reussie. Rapports disponibles dans les artifacts."
        }
        failure {
            mail to: "${EMAIL_TO}",
                 subject: "FAILURE - Build #${BUILD_NUMBER}",
                 body: "Build ${BUILD_NUMBER} echouee. Verifiez les logs Jenkins."
        }
    }
}
