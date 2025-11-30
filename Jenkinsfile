pipeline {
    agent {
        docker {
            image 'python:3.13-slim'  // Python + pip déjà présent
            args '-u root:root'        // pour installer des paquets et accéder à Docker
        }
    }

    environment {
        DOCKER_IMAGE = "devsecops-app"
        DOCKER_TAG   = "${BUILD_NUMBER}"
        APP_PORT     = "5000"
        EMAIL_TO     = "yass@entreprise.com"
        REPORT_DIR   = "reports"
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
            }
        }

        stage('Install Dependencies') {
            steps {
                echo 'Installation des dépendances Python...'
                sh '''
                    python -m pip install --upgrade pip
                    pip install -r requirements.txt
                '''
            }
        }

        stage('Code Quality & SAST') {
            steps {
                echo 'Analyse SAST et qualité du code...'
                sh '''
                    sonar-scanner \
                      -Dsonar.projectKey=DevSecOpsProject \
                      -Dsonar.sources=. \
                      -Dsonar.host.url=http://localhost:9000 \
                      -Dsonar.login=$SONARQUBE_TOKEN
                '''
            }
            post {
                always {
                    archiveArtifacts artifacts: '**/reports/sonar/*.xml', allowEmptyArchive: true
                }
            }
        }

        stage('Dependency Analysis (SCA)') {
            steps {
                echo 'Analyse des dépendances (Trivy / OWASP)...'
                sh '''
                    mkdir -p ${REPORT_DIR}
                    trivy fs --exit-code 1 --severity HIGH,CRITICAL --format json -o ${REPORT_DIR}/trivy.json .
                '''
            }
        }

        stage('Secrets Scan') {
            steps {
                echo 'Scan de secrets avec Gitleaks...'
                sh '''
                    mkdir -p ${REPORT_DIR}
                    gitleaks detect --source . --report-path ${REPORT_DIR}/gitleaks.json --exit-code 1
                '''
            }
        }

        stage('Build Docker Image') {
            steps {
                echo "Construction de l'image Docker ${DOCKER_IMAGE}:${DOCKER_TAG}..."
                sh "docker build -t ${DOCKER_IMAGE}:${DOCKER_TAG} ."
            }
        }

        stage('Docker Scan') {
            steps {
                echo 'Scan de l’image Docker...'
                sh '''
                    mkdir -p ${REPORT_DIR}
                    trivy image --exit-code 1 --severity HIGH,CRITICAL --format json -o ${REPORT_DIR}/docker_scan.json ${DOCKER_IMAGE}:${DOCKER_TAG}
                '''
            }
        }

        stage('Deploy to Staging') {
            steps {
                echo 'Déploiement en environnement staging...'
                sh "docker run -d -p ${APP_PORT}:5000 ${DOCKER_IMAGE}:${DOCKER_TAG}"
            }
        }

        stage('DAST Scan') {
            steps {
                echo 'Scan dynamique (DAST) de l’application...'
                sh '''
                    zap-cli -p 8080 quick-scan http://localhost:${APP_PORT} --self-contained --exit-code 1
                '''
            }
        }
    }

    post {
        always {
            echo 'Archivage des rapports...'
            archiveArtifacts artifacts: "${REPORT_DIR}/**", allowEmptyArchive: true
        }
        success {
            mail to: "${EMAIL_TO}",
                 subject: "SUCCESS - Build #${BUILD_NUMBER}",
                 body: "La build ${BUILD_NUMBER} a réussi. Tous les rapports ont été générés et archivés."
        }
        failure {
            mail to: "${EMAIL_TO}",
                 subject: "FAILURE - Build #${BUILD_NUMBER}",
                 body: "La build ${BUILD_NUMBER} a échoué. Vérifiez les logs et rapports pour corriger les problèmes critiques."
        }
    }
}

