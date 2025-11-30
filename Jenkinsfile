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
        
        stage('Create Virtual Environment') {
            steps {
                echo 'Creation environnement virtuel...'
                sh '''
                    python3 -m venv myenv
                    . myenv/bin/activate
                    pip install -r requirements.txt
                '''
            }
        }
        
        stage('SAST - Bandit Scan') {
            steps {
                echo 'Analyse statique avec Bandit...'
                sh '''
                    . myenv/bin/activate
                    pip install bandit
                    bandit -r . -f html -o reports/bandit_report.html
                '''
            }
        }
        
        stage('SCA - Dependency Check') {
            steps {
                echo 'Analyse des dependances...'
                sh '''
                    wget -q https://github.com/jeremylong/DependencyCheck/releases/download/v8.2.1/dependency-check-8.2.1-release.zip
                    unzip -q dependency-check-8.2.1-release.zip
                    ./dependency-check/bin/dependency-check.sh --scan . --format HTML --out reports/dependency-check-report.html
                '''
            }
        }
        
        stage('Secrets Detection') {
            steps {
                echo 'Detection des secrets...'
                sh '''
                    wget -q https://github.com/gitleaks/gitleaks/releases/download/v8.16.1/gitleaks_8.16.1_linux_x64.tar.gz
                    tar -xzf gitleaks_8.16.1_linux_x64.tar.gz
                    ./gitleaks detect -s . -r reports/gitleaks_report.json
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
                    wget -q https://github.com/aquasecurity/trivy/releases/download/v0.43.0/trivy_0.43.0_Linux-64bit.deb
                    dpkg -i trivy_0.43.0_Linux-64bit.deb
                    trivy image --format json --output reports/trivy_report.json ${DOCKER_IMAGE}:${DOCKER_TAG}
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
                    docker run --rm -v $(pwd)/reports:/zap/wrk/:rw owasp/zap2docker-stable zap-baseline.py -t http://host.docker.internal:5000 -J reports/zap_report.json
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
