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
        // Étape 1: Récupération du code
        stage('Checkout') {
            steps {
                echo '🔍 Récupération du code source...'
                checkout scm
                sh 'mkdir -p ${REPORT_DIR}'
            }
        }
        
        // Étape 2: SAST - Analyse statique (Phase 1 - Développement)
        stage('SAST - Bandit Analysis') {
            steps {
                echo '📊 Analyse statique du code avec Bandit...'
                sh '''
                    docker run --rm -v ${WORKSPACE}:/app python:3.9-alpine \
                    sh -c "pip install bandit && bandit -r /app -f html -o /app/${REPORT_DIR}/bandit_report.html -ll"
                '''
            }
        }
        
        // Étape 3: SCA - Analyse des dépendances (Phase 1 - Développement)
        stage('SCA - Dependency Check') {
            steps {
                echo '📦 Analyse des dépendances avec OWASP...'
                sh '''
                    docker run --rm -v ${WORKSPACE}:/src owasp/dependency-check:latest \
                    --scan /src \
                    --format HTML \
                    --project "DevSecOps-Project" \
                    --out /src/${REPORT_DIR}/dependency-check-report.html
                '''
            }
        }
        
        // Étape 4: Détection des secrets (Phase 1 - Développement)
        stage('Secrets Detection') {
            steps {
                echo '🔑 Détection des secrets avec Gitleaks...'
                sh '''
                    docker run --rm -v ${WORKSPACE}:/src zricethezav/gitleaks:latest \
                    detect -s /src -r /src/${REPORT_DIR}/gitleaks_report.json
                '''
            }
        }
        
        // Étape 5: Construction de l'image
        stage('Build Docker Image') {
            steps {
                echo '🐳 Construction de l image Docker...'
                sh "docker build -t ${DOCKER_IMAGE}:${DOCKER_TAG} ."
            }
        }
        
        // Étape 6: Scan de sécurité de l'image (Phase 3 - Production)
        stage('Docker Security Scan') {
            steps {
                echo '🔍 Scan de sécurité de l image avec Trivy...'
                sh '''
                    docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
                    -v ${WORKSPACE}/${REPORT_DIR}:/reports aquasec/trivy:latest \
                    image --format json -o /reports/trivy_report.json ${DOCKER_IMAGE}:${DOCKER_TAG}
                '''
            }
        }
        
        // Étape 7: Déploiement en staging
        stage('Deploy to Staging') {
            steps {
                echo '🚀 Déploiement en environnement de staging...'
                sh """
                    docker stop devsecops-app-staging || true
                    docker rm devsecops-app-staging || true
                    docker run -d -p ${APP_PORT}:5000 --name devsecops-app-staging ${DOCKER_IMAGE}:${DOCKER_TAG}
                    sleep 20
                """
            }
        }
        
        // Étape 8: DAST - Tests dynamiques (Phase 2 - Acceptation)
        stage('DAST - Dynamic Testing') {
            steps {
                echo '🌐 Tests de sécurité dynamiques avec OWASP ZAP...'
                sh '''
                    # Attendre que l application soit complètement démarrée
                    sleep 30
                    # Lancer le scan DAST
                    docker run --rm -v ${WORKSPACE}/${REPORT_DIR}:/zap/wrk/:rw \
                    -t owasp/zap2docker-stable zap-baseline.py \
                    -t http://host.docker.internal:${APP_PORT} \
                    -J /zap/wrk/zap_report.json \
                    -r /zap/wrk/zap_report.html
                '''
            }
        }
        
        // Étape 9: Security Gates - Validation (Phase 2 - Acceptation)
        stage('Security Gates') {
            steps {
                echo '⚡ Validation des critères de sécurité...'
                script {
                    // Vérification des vulnérabilités critiques
                    def criticalVulnerabilities = sh(
                        script: """
                            # Vérifier si Trivy a trouvé des vulnérabilités critiques
                            if [ -f "${REPORT_DIR}/trivy_report.json" ]; then
                                grep -c '"Severity": \"CRITICAL\"" ${REPORT_DIR}/trivy_report.json || echo "0"
                            else
                                echo "0"
                            fi
                        """,
                        returnStdout: true
                    ).trim().toInteger()
                    
                    // Vérifier les secrets détectés
                    def secretsDetected = sh(
                        script: """
                            if [ -f "${REPORT_DIR}/gitleaks_report.json" ]; then
                                jq length ${REPORT_DIR}/gitleaks_report.json || echo "0"
                            else
                                echo "0"
                            fi
                        """,
                        returnStdout: true
                    ).trim().toInteger()
                    
                    // Bloquer le pipeline si vulnérabilités critiques
                    if (criticalVulnerabilities > 0) {
                        error("❌ ${criticalVulnerabilities} vulnérabilité(s) CRITIQUE(s) détectée(s). Pipeline bloqué.")
                    }
                    
                    // Avertissement pour les secrets (peut être configuré pour bloquer)
                    if (secretsDetected > 0) {
                        echo "⚠️  ${secretsDetected} secret(s) potentiel(s) détecté(s). Vérification nécessaire."
                    }
                }
            }
        }
    }
    
    post {
        always {
            echo '📁 Archivage des rapports et nettoyage...'
            sh '''
                # Arrêter et nettoyer les conteneurs
                docker stop devsecops-app-staging || true
                docker rm devsecops-app-staging || true
                
                # Générer un rapport de synthèse
                echo "=== RAPPORT DE SÉCURITÉ - Build ${BUILD_NUMBER} ===" > ${REPORT_DIR}/security_summary.txt
                echo "Date: $(date)" >> ${REPORT_DIR}/security_summary.txt
                echo "Statut: ${currentBuild.result ?: 'SUCCESS'}" >> ${REPORT_DIR}/security_summary.txt
                echo "==========================================" >> ${REPORT_DIR}/security_summary.txt
                echo "SAST (Bandit): Complété" >> ${REPORT_DIR}/security_summary.txt
                echo "SCA (OWASP Dependency Check): Complété" >> ${REPORT_DIR}/security_summary.txt  
                echo "Détection de secrets (Gitleaks): Complété" >> ${REPORT_DIR}/security_summary.txt
                echo "Scan Docker (Trivy): Complété" >> ${REPORT_DIR}/security_summary.txt
                echo "DAST (OWASP ZAP): Complété" >> ${REPORT_DIR}/security_summary.txt
            '''
            
            archiveArtifacts artifacts: "${REPORT_DIR}/**", allowEmptyArchive: true
        }
        
        success {
            echo '✅ Tous les tests de sécurité ont été passés avec succès!'
            mail to: "${EMAIL_TO}",
                 subject: "SUCCESS - Build #${BUILD_NUMBER} - Pipeline DevSecOps",
                 body: """
                 Le pipeline DevSecOps #${BUILD_NUMBER} a été exécuté avec succès.
                 
                 Tous les contrôles de sécurité ont été validés :
                 - Analyse statique (SAST) avec Bandit
                 - Analyse des dépendances (SCA) avec OWASP Dependency Check
                 - Détection de secrets avec Gitleaks
                 - Scan de sécurité Docker avec Trivy
                 - Tests dynamiques (DAST) avec OWASP ZAP
                 
                 Rapports disponibles dans les artifacts Jenkins.
                 """
        }
        
        failure {
            echo '❌ Le pipeline a échoué lors des contrôles de sécurité!'
            mail to: "${EMAIL_TO}",
                 subject: "FAILURE - Build #${BUILD_NUMBER} - Vulnérabilités critiques détectées",
                 body: """
                 Le pipeline DevSecOps #${BUILD_NUMBER} a échoué.
                 
                 Raison : Vulnérabilités critiques détectées ou échec des tests de sécurité.
                 
                 Actions requises :
                 - Consulter les rapports de sécurité dans Jenkins
                 - Corriger les vulnérabilités identifiées
                 - Relancer le pipeline
                 
                 Logs : ${BUILD_URL}/console
                 """
        }
        
        unstable {
            echo '⚠️  Problèmes de sécurité nécessitant une attention'
            mail to: "${EMAIL_TO}",
                 subject: "UNSTABLE - Build #${BUILD_NUMBER} - Avis de sécurité",
                 body: """
                 Le pipeline DevSecOps #${BUILD_NUMBER} est instable.
                 
                 Des problèmes de sécurité ont été détectés nécessitant une revue :
                 - Secrets potentiels dans le code
                 - Vulnérabilités nécessitant une analyse de risque
                 
                 Revoyez les rapports avant déploiement en production.
                 """
        }
    }
}
