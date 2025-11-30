pipeline {
    agent any

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
                // Utiliser python3 -m pip explicitement pour éviter l'erreur pip not found
                sh '''
                python3 -m ensurepip --upgrade
                python3 -m pip install --upgrade pip
                python3 -m pip install -r requirements.txt
                '''
            }
        }

        stage('Pre-commit & Bandit Scan') {
            steps {
                echo 'Analyse du code avec pre-commit et Bandit...'
                sh '''
                python3 -m pip install pre-commit bandit
                pre-commit run --all-files
                bandit -r . -ll
                '''
            }
        }

        stage('Build Docker Image') {
            steps {
                echo "Construction de l'image Docker ${DOCKER_IMAGE}:${DOCKER_TAG}..."
                sh "docker build -t ${DOCKER_IMAGE}:${DOCKER_TAG} ."
            }
        }

        stage('Deploy to Staging') {
            steps {
                echo 'Déploiement de l’application en staging...'
                sh "docker run -d -p ${APP_PORT}:5000 ${DOCKER_IMAGE}:${DOCKER_TAG}"
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

