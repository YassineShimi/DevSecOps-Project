pipeline {
    agent any
    environment {
        DOCKER_IMAGE = "devsecops-app"
        DOCKER_TAG   = "${BUILD_NUMBER}"
        APP_PORT     = "5000"
        EMAIL_TO     = "yass@entreprise.com"
        REPORT_DIR   = "reports"
        SONARQUBE_URL = "http://sonarqube:9000"
    }
    options {
        timestamps()
        buildDiscarder(logRotator(numToKeepStr: '10'))
    }
    stages {
        stage('Checkout') {
            steps {
                echo 'Récupération du code source...'
                checkout scm
                sh 'mkdir -p ${REPORT_DIR}'
            }
        }
        
        stage('Install Dependencies') {
            steps {
                echo 'Installation des dépendances Python...'
                sh '''
                python3 --version
                pip3 --version
                pip3 install -r requirements.txt
                '''
            }
        }
        
        stage('SAST - Bandit Scan') {
            steps {
                echo 'Analyse statique du code avec Bandit...'
                sh '''
                pip3 install bandit
                bandit -r . -f html -o ${REPORT_DIR}/bandit_report.html -ll
                '''
            }
            post {
                always {
                    echo 'Rapport Bandit généré'
                }
            }
        }
        
        stage('SAST - SonarQube Analysis') {
            steps {
                echo 'Analyse avec SonarQube...'
                sh '''
                pip3 install sonarqube-api
                # Ici vous ajouteriez l'appel à SonarQube Scanner
                echo "SonarQube analysis would run here"
                '''
            }
        }
        
        stage('SCA - Dependency Check') {
            steps {
                echo 'Analyse des dépendances avec OWASP Dependency Check...'
                sh '''
                # Installation et exécution de OWASP Dependency Check
                wget -O dependency-check.zip https://github.com/jeremylong/DependencyCheck/releases/download/v8.2.1/dependency-check-8.2.1-release.zip
                unzip dependency-check.zip
                ./dependency-check/bin/dependency-check.sh --scan . --format HTML --out ${REPORT_DIR}/dependency-check-report.html
                '''
            }
        }
        
        stage('Secrets Detection') {
            steps {
                echo 'Détection des secrets avec Gitleaks...'
                sh '''
                # Installation de Gitleaks
                wget -O gitleaks.tar.gz https://github.com/gitleaks/gitleaks/releases/download/v8.16.1/gitleaks_8.16.1_linux_x64.tar.gz
                tar -xzf gitleaks.tar.gz
                ./gitleaks detect -s . -r ${REPORT_DIR}/gitleaks_report.json
                '''
            }
        }
        
        stage('Build Docker Image') {
            steps {
                echo "Construction de l'image Docker ${DOCKER_IMAGE}:${DOCKER_TAG}..."
                sh "docker build -t ${DOCKER_IMAGE}:${DOCKER_TAG} ."
            }
        }
        
        stage('Docker Image Security Scan') {
            steps {
                echo "Scan de sécurité de l'image Docker avec Trivy..."
                sh '''
                # Installation de Trivy
                wget -O trivy.deb https://github.com/aquasecurity/trivy/releases/download/v0.43.0/trivy_0.43.0_Linux-64bit.deb
                sudo dpkg -i trivy.deb
                trivy image --format json --output ${REPORT_DIR}/trivy_report.json ${DOCKER_IMAGE}:${DOCKER_TAG}
                '''
            }
        }
        
        stage('Deploy to Staging') {
            steps {
                echo 'Déploiement de l'application en staging...'
                sh "docker run -d -p ${APP_PORT}:5000 --name devsecops-app ${DOCKER_IMAGE}:${DOCKER_TAG}"
                // Attendre que l'application soit démarrée
                sh 'sleep 30'
            }
        }
        
        stage('DAST - Dynamic Testing') {
            steps {
                echo 'Test de sécurité dynamique avec ZAP...'
                sh '''
                docker run -v ${WORKSPACE}/${REPORT_DIR}:/zap/wrk/:rw \
                  -t owasp/zap2docker-stable zap-baseline.py \
                  -t http://host.docker.internal:${APP_PORT} \
                  -J zap_report.json
                '''
            }
        }
    }
    post {
        always {
            echo 'Nettoyage et archivage des rapports...'
            sh 'docker stop devsecops-app || true'
            sh 'docker rm devsecops-app || true'
            archiveArtifacts artifacts: "${REPORT_DIR}/**", allowEmptyArchive: true
            publishHTML([
                allowMissing: false,
                alwaysLinkToLastBuild: true,
                keepAll: true,
                reportDir: '${REPORT_DIR}',
                reportFiles: 'bandit_report.html,dependency-check-report.html',
                reportName: 'Security Reports'
            ])
        }
        success {
            mail to: "${EMAIL_TO}",
                 subject: "SUCCESS - Build #${BUILD_NUMBER}",
                 body: """
                 La build ${BUILD_NUMBER} a réussi.
                 
                 Rapports de sécurité générés :
                 - Bandit (SAST) : ${BUILD_URL}/Security_20Reports/bandit_report.html
                 - OWASP Dependency Check : ${BUILD_URL}/Security_20Reports/dependency-check-report.html
                 - Gitleaks : ${BUILD_URL}/artifact/${REPORT_DIR}/gitleaks_report.json
                 - Trivy : ${BUILD_URL}/artifact/${REPORT_DIR}/trivy_report.json
                 """
        }
        failure {
            mail to: "${EMAIL_TO}",
                 subject: "FAILURE - Build #${BUILD_NUMBER}",
                 body: """
                 La build ${BUILD_NUMBER} a échoué.
                 
                 Consultez les logs pour identifier les problèmes :
                 ${BUILD_URL}/console
                 
                 Rapports disponibles : ${BUILD_URL}/Security_20Reports/
                 """
        }
    }
}
