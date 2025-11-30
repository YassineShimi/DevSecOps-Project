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
        
        stage('SAST - Bandit Analysis') {
            steps {
                echo 'Analyse statique du code avec Bandit...'
                sh '''
                    docker run --rm -v ${WORKSPACE}:/app python:3.9-alpine \
                    sh -c "mkdir -p /app/reports && pip install bandit && bandit -r /app -f html -o /app/reports/bandit_report.html -ll"
                '''
            }
        }
        
        stage('SCA - Dependency Check') {
            steps {
                echo 'Analyse rapide des dependances avec Trivy...'
                sh '''
                    # Analyser les dependances du projet
                    docker run --rm -v ${WORKSPACE}:/app aquasec/trivy:latest \
                    fs --format json --output /app/reports/trivy_fs_report.json /app
                    
                    # Generer aussi un rapport HTML pour visualisation
                    docker run --rm -v ${WORKSPACE}:/app aquasec/trivy:latest \
                    fs --format html --output /app/reports/trivy_fs_report.html /app
                '''
            }
        }
        
        stage('Secrets Detection') {
            steps {
                echo 'Detection des secrets avec Gitleaks...'
                sh '''
                    docker run --rm -v ${WORKSPACE}:/src zricethezav/gitleaks:latest \
                    detect -s /src -r /src/reports/gitleaks_report.json
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
                echo 'Scan securite Docker avec Trivy...'
                sh '''
                    docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
                    -v ${WORKSPACE}/reports:/reports aquasec/trivy:latest \
                    image --format json --output /reports/trivy_image_report.json ${DOCKER_IMAGE}:${DOCKER_TAG}
                    
                    # Rapport HTML pour l'image
                    docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
                    -v ${WORKSPACE}/reports:/reports aquasec/trivy:latest \
                    image --format html --output /reports/trivy_image_report.html ${DOCKER_IMAGE}:${DOCKER_TAG}
                '''
            }
        }
        
        stage('Deploy to Staging') {
            steps {
                echo 'Deploiement en environnement de staging...'
                sh """
                    docker stop devsecops-app-staging || true
                    docker rm devsecops-app-staging || true
                    docker run -d -p ${APP_PORT}:5000 --name devsecops-app-staging ${DOCKER_IMAGE}:${DOCKER_TAG}
                    sleep 20
                """
            }
        }
        
        stage('DAST - Dynamic Testing') {
            steps {
                echo 'Tests de securite dynamiques avec OWASP ZAP...'
                sh '''
                    sleep 30
                    docker run --rm -v ${WORKSPACE}/reports:/zap/wrk/:rw \
                    -t owasp/zap2docker-stable zap-baseline.py \
                    -t http://host.docker.internal:5000 \
                    -J /zap/wrk/zap_report.json \
                    -r /zap/wrk/zap_report.html
                '''
            }
        }
        
        stage('Security Gates') {
            steps {
                echo 'Validation des criteres de securite...'
                script {
                    // Vérifier si les rapports existent
                    def banditReport = fileExists 'reports/bandit_report.html'
                    def trivyFSReport = fileExists 'reports/trivy_fs_report.json'
                    def trivyImageReport = fileExists 'reports/trivy_image_report.json'
                    def zapReport = fileExists 'reports/zap_report.json'
                    
                    if (!banditReport) {
                        echo "Avertissement: Rapport Bandit manquant"
                    }
                    if (!trivyFSReport) {
                        echo "Avertissement: Rapport Trivy FS manquant"
                    }
                    if (!trivyImageReport) {
                        echo "Avertissement: Rapport Trivy Image manquant"
                    }
                    if (!zapReport) {
                        echo "Avertissement: Rapport ZAP manquant"
                    }
                    
                    // Vérification des vulnérabilités critiques dans Trivy FS
                    if (trivyFSReport) {
                        def criticalVulnerabilitiesFS = sh(
                            script: """
                                grep -c '"Severity": "CRITICAL"' reports/trivy_fs_report.json || echo "0"
                            """,
                            returnStdout: true
                        ).trim().toInteger()
                        
                        if (criticalVulnerabilitiesFS > 0) {
                            error("${criticalVulnerabilitiesFS} vulnerabilite(s) CRITIQUE(s) detectee(s) dans les dependances. Pipeline bloque.")
                        }
                    }
                    
                    // Vérification des vulnérabilités critiques dans Trivy Image
                    if (trivyImageReport) {
                        def criticalVulnerabilitiesImage = sh(
                            script: """
                                grep -c '"Severity": "CRITICAL"' reports/trivy_image_report.json || echo "0"
                            """,
                            returnStdout: true
                        ).trim().toInteger()
                        
                        if (criticalVulnerabilitiesImage > 0) {
                            error("${criticalVulnerabilitiesImage} vulnerabilite(s) CRITIQUE(s) detectee(s) dans l'image Docker. Pipeline bloque.")
                        }
                    }
                    
                    // Vérification des secrets (si le rapport existe)
                    if (fileExists('reports/gitleaks_report.json')) {
                        def secretsDetected = sh(
                            script: """
                                jq length reports/gitleaks_report.json || echo "0"
                            """,
                            returnStdout: true
                        ).trim().toInteger()
                        
                        if (secretsDetected > 0) {
                            echo "${secretsDetected} secret(s) potentiel(s) detecte(s). Verification necessaire."
                        }
                    }
                    
                    echo "Tous les controles de securite ont ete executes avec succes"
                }
            }
        }
    }
    
    post {
        always {
            echo 'Archivage des rapports et nettoyage...'
            sh '''
                docker stop devsecops-app-staging || true
                docker rm devsecops-app-staging || true
                
                echo "=== RAPPORT DE SECURITE - Build ''' + env.BUILD_NUMBER + ''' ===" > reports/security_summary.txt
                echo "Date: $(date)" >> reports/security_summary.txt
                echo "Statut: ''' + currentBuild.result + '''" >> reports/security_summary.txt
                echo "==========================================" >> reports/security_summary.txt
                echo "SAST (Bandit): ''' + (fileExists('reports/bandit_report.html') ? 'Complete' : 'Echec') + '''" >> reports/security_summary.txt
                echo "SCA (Trivy FS): ''' + (fileExists('reports/trivy_fs_report.json') ? 'Complete' : 'Echec') + '''" >> reports/security_summary.txt
                echo "Detection de secrets (Gitleaks): ''' + (fileExists('reports/gitleaks_report.json') ? 'Complete' : 'Echec') + '''" >> reports/security_summary.txt
                echo "Scan Docker (Trivy Image): ''' + (fileExists('reports/trivy_image_report.json') ? 'Complete' : 'Echec') + '''" >> reports/security_summary.txt
                echo "DAST (OWASP ZAP): ''' + (fileExists('reports/zap_report.json') ? 'Complete' : 'Echec') + '''" >> reports/security_summary.txt
            '''
            
            archiveArtifacts artifacts: "reports/**", allowEmptyArchive: true
        }
        
        success {
            echo 'Tous les tests de securite ont ete passes avec succes!'
            mail to: "${EMAIL_TO}",
                 subject: "SUCCESS - Build #${BUILD_NUMBER} - Pipeline DevSecOps",
                 body: """
                 Le pipeline DevSecOps #${BUILD_NUMBER} a ete execute avec succes.
                 
                 Tous les controles de securite ont ete valides :
                 - Analyse statique (SAST) avec Bandit
                 - Analyse des dependances (SCA) avec Trivy
                 - Detection de secrets avec Gitleaks
                 - Scan de securite Docker avec Trivy
                 - Tests dynamiques (DAST) avec OWASP ZAP
                 
                 Rapports disponibles dans les artifacts Jenkins.
                 """
        }
        
        failure {
            echo 'Le pipeline a echoue lors des controles de securite!'
            mail to: "${EMAIL_TO}",
                 subject: "FAILURE - Build #${BUILD_NUMBER} - Vulnerabilites critiques detectees",
                 body: """
                 Le pipeline DevSecOps #${BUILD_NUMBER} a echoue.
                 
                 Raison : Vulnerabilites critiques detectees ou echec des tests de securite.
                 
                 Actions requises :
                 - Consulter les rapports de securite dans Jenkins
                 - Corriger les vulnerabilites identifiees
                 - Relancer le pipeline
                 
                 Logs : ${BUILD_URL}/console
                 """
        }
    }
}
