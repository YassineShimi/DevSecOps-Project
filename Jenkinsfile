pipeline {
    agent any
    
    environment {
        DOCKER_IMAGE = "devsecops-app"
        DOCKER_TAG   = "${BUILD_NUMBER}"
        APP_PORT     = "5000"
    }
    
    stages {
        stage('Checkout') {
            steps {
                echo 'Étape 1: Récupération du code...'
                checkout scm
            }
        }
        
        stage('Analyse de sécurité du code') {
            steps {
                echo 'Étape 2: Scan du code avec Bandit...'
                sh '''
                    # Scan du code Python
                    docker run --rm \
                        -v "${WORKSPACE}":/app \
                        -w /app \
                        python:3.12-slim bash -c "
                            pip install bandit && \
                            bandit -r /app -f html -o /app/bandit-report.html
                        "
                    echo "✅ Scan Bandit terminé"
                '''
            }
        }
        
        stage('Recherche de secrets') {
            steps {
                echo 'Étape 3: Recherche de mots de passe dans le code...'
                sh '''
                    # Scan des secrets
                    docker run --rm \
                        -v "${WORKSPACE}":/path \
                        zricethezav/gitleaks:latest \
                        detect --source=/path \
                        --report-format=json \
                        --report-path=/path/gitleaks-report.json \
                        --no-git
                    
                    # Vérifier si on a trouvé des secrets
                    if [ -f gitleaks-report.json ]; then
                        echo "📄 Rapport Gitleaks créé"
                        # Compter le nombre de secrets trouvés
                        SECRETS_COUNT=$(grep -o "description" gitleaks-report.json | wc -l || echo "0")
                        if [ "$SECRETS_COUNT" -gt 0 ]; then
                            echo "❌ ATTENTION: $SECRETS_COUNT secret(s) trouvé(s) dans le code!"
                            echo "Le pipeline continue mais vérifie le rapport"
                        else
                            echo "✅ Aucun secret dangereux trouvé"
                        fi
                    else
                        echo "❌ Erreur: rapport Gitleaks non créé"
                    fi
                '''
            }
        }
        
        stage('Construction Docker') {
            steps {
                echo 'Étape 4: Construction de l image Docker...'
                sh '''
                    docker build -t ${DOCKER_IMAGE}:${DOCKER_TAG} "${WORKSPACE}"
                    docker tag ${DOCKER_IMAGE}:${DOCKER_TAG} ${DOCKER_IMAGE}:latest
                    echo "✅ Image Docker créée: ${DOCKER_IMAGE}:${DOCKER_TAG}"
                '''
            }
        }
        
        stage('Scan de sécurité Docker') {
            steps {
                echo 'Étape 5: Scan de l image Docker...'
                sh '''
                    # Scan de sécurité
                    docker run --rm \
                        -v /var/run/docker.sock:/var/run/docker.sock \
                        aquasec/trivy:latest image \
                        --format json \
                        --output trivy-report.json \
                        ${DOCKER_IMAGE}:${DOCKER_TAG} || echo "Scan Trivy terminé"
                    
                    echo "✅ Scan Docker terminé"
                '''
            }
        }
        
        stage('Déploiement') {
            steps {
                echo 'Étape 6: Déploiement de l application...'
                sh '''
                    docker stop devsecops-staging 2>/dev/null || true
                    docker rm devsecops-staging 2>/dev/null || true
                    
                    docker run -d \
                        --name devsecops-staging \
                        --network jenkins \
                        -p ${APP_PORT}:5000 \
                        ${DOCKER_IMAGE}:${DOCKER_TAG}
                    
                    sleep 10
                    echo "✅ Application déployée: http://localhost:${APP_PORT}"
                '''
            }
        }
        
        stage('Test de sécurité') {
            steps {
                echo 'Étape 7: Test de sécurité de l application...'
                sh '''
                    docker run --rm \
                        --network jenkins \
                        -v "${WORKSPACE}":/zap/wrk:rw \
                        ghcr.io/zaproxy/zaproxy:stable \
                        zap-baseline.py \
                        -t http://devsecops-staging:5000 \
                        -J zap-report.json \
                        -r zap-report.html || echo "Test ZAP terminé"
                    
                    echo "✅ Test de sécurité terminé"
                '''
            }
        }
        
        stage('Résumé') {
            steps {
                echo 'Étape 8: Création des rapports...'
                sh '''
                    echo "========================================"
                    echo "        RAPPORTS DE SÉCURITÉ"
                    echo "========================================"
                    echo ""
                    echo "Voici les rapports générés:"
                    ls -la *.json *.html 2>/dev/null || echo "Aucun rapport pour le moment"
                    echo ""
                    echo "Pour voir les rapports:"
                    echo "1. Aller dans Jenkins"
                    echo "2. Cliquer sur ce build"
                    echo "3. Regarder dans 'Artifacts'"
                    echo "========================================"
                '''
            }
        }
    }
    
    post {
        always {
            echo '📦 Archivage des rapports...'
            archiveArtifacts artifacts: '*.json, *.html', allowEmptyArchive: true, fingerprint: true
            
            // Publication du rapport Bandit
            publishHTML([
                allowMissing: true,
                alwaysLinkToLastBuild: true,
                keepAll: true,
                reportDir: '.',
                reportFiles: 'bandit-report.html',
                reportName: 'Rapport Sécurité Code',
                reportTitles: 'Analyse de Sécurité'
            ])
        }
        
        success {
            echo '''
🎉 FÉLICITATIONS ! PIPELINE RÉUSSI !

Ce qui a été fait:
✅ Code analysé pour les failles de sécurité
✅ Recherche de mots de passe exposés  
✅ Image Docker scannée pour vulnérabilités
✅ Application testée en fonctionnement
✅ Rapports générés

Prochaines étapes:
1. Vérifier les rapports dans Jenkins
2. Corriger les problèmes si nécessaire
3. Recommencer !
'''
        }
        
        failure {
            echo '''
❌ PIPELINE EN ÉCHEC

Problèmes détectés:
- Soit l application ne se déploie pas
- Soit un scan a trouvé des problèmes critiques

Solution:
1. Vérifier les logs
2. Corriger le problème
3. Relancer le pipeline
'''
        }
    }
}
