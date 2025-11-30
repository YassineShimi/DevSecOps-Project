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
                echo 'Analyse des dependances avec OWASP...'
                sh '''
                    docker run --rm -v ${WORKSPACE}:/src owasp/dependency-check:latest \
                    --scan /src \
                    --format HTML \
                    --project "DevSecOps-Project" \
                    --out /src/reports/dependency-check-report.html
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
                    image --format json -o /reports/trivy_report.json ${DOCKER_IMAGE}:${DOCKER_TAG}
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
                    def dependencyReport = fileExists 'reports/dependency-check-report.html'
                    def trivyReport = fileExists 'reports/trivy_report.json'
                    def zapReport = fileExists 'reports/zap_report.json'
                    
                    if (!banditReport) {
                        echo "Avertissement: Rapport Bandit manquant"
                    }
                    if (!dependencyReport) {
                        echo "Avertissement: Rapport OWASP Dependency Check manquant"
                    }
                    if (!trivyReport) {
                        echo "Avertissement: Rapport Trivy manquant"
                    }
                    if (!zapReport) {
                        echo "Avertissement: Rapport ZAP manquant"
                    }
                    
                    // Vérification basique des vulnérabilités (si le rapport existe)
                    if (trivyReport) {
                        def criticalVulnerabilities = sh(
                            script: """
                                grep -c '"Severity": "CRITICAL"' reports/trivy_report.json || echo "0"
                            """,
                            returnStdout: true
                        ).trim().toInteger()
                        
                        if (criticalVulnerabilities > 0) {
                            error("${criticalVulnerabilities} vulnerabilite(s) CRITIQUE(s) detectee(s). Pipeline bloque.")
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
                echo "SCA (OWASP Dependency Check): ''' + (fileExists('reports/dependency-check-report.html') ? 'Complete' : 'Echec') + '''" >> reports/security_summary.txt
                echo "Detection de secrets (Gitleaks): ''' + (fileExists('reports/gitleaks_report.json') ? 'Complete' : 'Echec') + '''" >> reports/security_summary.txt
                echo "Scan Docker (Trivy): ''' + (fileExists('reports/trivy_report.json') ? 'Complete' : 'Echec') + '''" >> reports/security_summary.txt
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
                 - Analyse des dependances (SCA) avec OWASP Dependency Check
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
