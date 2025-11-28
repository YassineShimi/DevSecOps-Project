pipeline {
    agent any
    
    environment {
        DOCKER_IMAGE = "devsecops-app"
        DOCKER_TAG = "${BUILD_NUMBER}"
        APP_PORT = "5000"
    }
    
    stages {
        stage(' Checkout') {
            steps {
                echo ' Récupération du code source...'
                checkout scm
            }
        }
        
        stage('SAST - Analyse statique') {
            steps {
                echo ' Analyse du code avec Bandit...'
                sh '''
                    pip3 install bandit || true
                    bandit -r . -f json -o bandit-report.json || true
                    bandit -r . -f html -o bandit-report.html || true
                    echo "Rapport Bandit généré"
                '''
            }
        }
        
        stage(' SCA - Analyse des dépendances') {
            steps {
                echo ' Vérification des vulnérabilités dans les dépendances...'
                sh '''
                    pip3 install safety || true
                    safety check --json --output safety-report.json || true
                    safety check || true
                '''
            }
        }
        
        stage(' Secrets Scanning') {
            steps {
                echo ' Recherche de secrets exposés avec Gitleaks...'
                sh '''
                    docker pull zricethezav/gitleaks:latest
                    docker run --rm -v $(pwd):/path zricethezav/gitleaks:latest \
                        detect --source="/path" \
                        --report-format=json \
                        --report-path=/path/gitleaks-report.json \
                        --no-git || echo "Secrets détectés (attendu pour la démo)"
                '''
            }
        }
        
        stage('Build Docker Image') {
            steps {
                echo ' Construction de l\'image Docker...'
                sh '''
                    docker build -t ${DOCKER_IMAGE}:${DOCKER_TAG} .
                    docker tag ${DOCKER_IMAGE}:${DOCKER_TAG} ${DOCKER_IMAGE}:latest
                    echo "Image créée: ${DOCKER_IMAGE}:${DOCKER_TAG}"
                '''
            }
        }
        
        stage(' Docker Security Scan') {
            steps {
                echo ' Scan de sécurité de l\'image avec Trivy...'
                sh '''
                    docker pull aquasec/trivy:latest
                    docker run --rm \
                        -v /var/run/docker.sock:/var/run/docker.sock \
                        -v $(pwd):/output \
                        aquasec/trivy:latest image \
                        --format json \
                        --output /output/trivy-report.json \
                        ${DOCKER_IMAGE}:${DOCKER_TAG} || true
                    
                    docker run --rm \
                        -v /var/run/docker.sock:/var/run/docker.sock \
                        aquasec/trivy:latest image \
                        --severity HIGH,CRITICAL \
                        ${DOCKER_IMAGE}:${DOCKER_TAG} || true
                '''
            }
        }
        
        stage(' Deploy to Staging') {
            steps {
                echo ' Déploiement en environnement de test...'
                sh '''
                    # Arrêter l'ancien conteneur s'il existe
                    docker stop devsecops-staging 2>/dev/null || true
                    docker rm devsecops-staging 2>/dev/null || true
                    
                    # Lancer le nouveau conteneur
                    docker run -d \
                        --name devsecops-staging \
                        --network jenkins \
                        -p ${APP_PORT}:5000 \
                        ${DOCKER_IMAGE}:${DOCKER_TAG}
                    
                    # Attendre que l'app démarre
                    sleep 10
                    
                    # Vérifier que l'app répond
                    curl -f http://localhost:${APP_PORT} || exit 1
                    echo " Application déployée sur http://localhost:${APP_PORT}"
                '''
            }
        }
        
        stage(' DAST - Tests dynamiques') {
            steps {
                echo 'Scan de sécurité dynamique avec OWASP ZAP...'
                sh '''
                    docker pull owasp/zap2docker-stable
                    
                    # Scan baseline (rapide)
                    docker run --rm \
                        --network jenkins \
                        -v $(pwd):/zap/wrk:rw \
                        owasp/zap2docker-stable \
                        zap-baseline.py \
                        -t http://devsecops-staging:5000 \
                        -J zap-report.json \
                        -r zap-report.html || echo "Vulnérabilités détectées (attendu)"
                '''
            }
        }
        
        stage('Security Gate') {
            steps {
                echo 'Vérification des seuils de sécurité...'
                script {
                    echo '''
                    ═══════════════════════════════════════
                     RÉSUMÉ DES CONTRÔLES DE SÉCURITÉ
                    ═══════════════════════════════════════
                    ✓ SAST (Bandit)     : Terminé
                    ✓ SCA (Safety)      : Terminé
                    ✓ Secrets (Gitleaks): Terminé
                    ✓ Docker (Trivy)    : Terminé
                    ✓ DAST (OWASP ZAP)  : Terminé
                    ═══════════════════════════════════════
                    '''
                    
                    // En production, vous ajouteriez des conditions ici
                    // Exemple:
                    // if (criticalVulnerabilities > 0) {
                    //     error(" Vulnérabilités critiques détectées!")
                    // }
                }
            }
        }
    }
    
    post {
        always {
            echo 'Archivage des rapports...'
            archiveArtifacts artifacts: '*-report.*', allowEmptyArchive: true
            
            // Publier les rapports HTML
            publishHTML([
                allowMissing: true,
                alwaysLinkToLastBuild: true,
                keepAll: true,
                reportDir: '.',
                reportFiles: 'bandit-report.html, zap-report.html',
                reportName: 'Security Reports'
            ])
        }
	success {
  	  echo """
═══════════════════════════════════════
PIPELINE TERMINÉ AVEC SUCCÈS !
═══════════════════════════════════════
"""
}
f	ailure {
   	 echo """
═══════════════════════════════════════
PIPELINE ÉCHOUÉ - Consultez les logs
═══════════════════════════════════════
"""
}
    }
}
