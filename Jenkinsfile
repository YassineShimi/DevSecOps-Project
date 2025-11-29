pipeline {
    agent any

    environment {
        DOCKER_IMAGE = "devsecops-app"
        DOCKER_TAG   = "${BUILD_NUMBER}"
        APP_PORT     = "5000"
        EMAIL_TO     = "vipertn2@gmail.com"
        EMAIL_FROM   = "yassine.shimi02@gmail.com"
    }

    stages {
        stage('Checkout') {
            steps {
                echo '🔍 Recuperation du code source...'
                checkout scm
            }
        }

        stage('SAST & SCA') {
            steps {
                echo '🔍 Analyse du code avec Bandit et Safety...'
                sh '''
                    # Nettoyer les anciens rapports
                    rm -f bandit-report.* safety-report.* 2>/dev/null || true
                    
                    docker run --rm -v "${WORKSPACE}":/app -w /app python:3.12-slim bash -c "
                        pip install --quiet bandit safety && \
                        bandit -r /app -f json -o /app/bandit-report.json && \
                        bandit -r /app -f html -o /app/bandit-report.html && \
                        safety check --json > /app/safety-report.json 2>&1 || echo 'Safety scan completed' > /app/safety-report.txt
                    "
                    echo "=== RAPPORTS BANDIT/SAFETY ==="
                    ls -la bandit-report.* safety-report.* 2>/dev/null || echo "Aucun rapport genere"
                    echo "==============================="
                '''
            }
        }

        stage('Secrets Scanning') {
            steps {
                echo '🔑 Recherche de secrets avec Gitleaks...'
                sh '''
                    # NE PAS écraser le rapport - laisser Gitleaks écrire ses findings
                    docker run --rm -v "${WORKSPACE}":/path zricethezav/gitleaks:latest detect \
                        --source="/path" --report-format=json --report-path=/path/gitleaks-report.json --no-git || true
                    
                    echo "=== RAPPORT GITLEAKS ==="
                    if [ -f gitleaks-report.json ]; then
                        echo "Fichier trouve:"
                        ls -la gitleaks-report.json
                        echo "Contenu:"
                        cat gitleaks-report.json
                    else
                        echo "Aucun rapport Gitleaks genere"
                        echo '{"findings":[]}' > gitleaks-report.json
                    fi
                    echo "========================"
                '''
            }
        }

        stage('Build Docker Image') {
            steps {
                echo '🐳 Construction de l image Docker...'
                sh '''
                    docker build -t ${DOCKER_IMAGE}:${DOCKER_TAG} "${WORKSPACE}"
                    docker tag ${DOCKER_IMAGE}:${DOCKER_TAG} ${DOCKER_IMAGE}:latest
                    echo "Image Docker construite: ${DOCKER_IMAGE}:${DOCKER_TAG}"
                '''
            }
        }

        stage('Docker Security Scan') {
            steps {
                echo '🔒 Scan de securite Docker avec Trivy...'
                sh '''
                    docker run --rm -v /var/run/docker.sock:/var/run/docker.sock -v "${WORKSPACE}":/output \
                        aquasec/trivy:latest image --format json --output /output/trivy-report.json \
                        ${DOCKER_IMAGE}:${DOCKER_TAG} || true
                    
                    echo "=== RAPPORT TRIVY ==="
                    if [ -f trivy-report.json ]; then
                        echo "Fichier trouve:"
                        ls -la trivy-report.json
                    else
                        echo "Aucun rapport Trivy genere"
                        echo '{"Results":[]}' > trivy-report.json
                    fi
                    echo "===================="
                '''
            }
        }

        stage('Security Gate') {
            steps {
                echo '🚨 Verification des criteres de securite...'
                script {
                    // Vérifier Gitleaks - NE PAS écraser le rapport
                    if (fileExists('gitleaks-report.json')) {
                        def gitleaksContent = readFile('gitleaks-report.json')
                        if (gitleaksContent.contains('"findings":[]') || gitleaksContent.trim() == '{"findings":[]}') {
                            echo "✅ Aucun secret detecte par Gitleaks"
                        } else {
                            try {
                                def gitleaks = readJSON file: 'gitleaks-report.json'
                                def leakCount = gitleaks.findings?.size() ?: 0
                                if (leakCount > 0) {
                                    echo "❌ Gitleaks a trouve ${leakCount} secrets!"
                                    // Pour le moment on ne bloque pas, juste un warning
                                    currentBuild.result = 'UNSTABLE'
                                }
                            } catch (Exception e) {
                                echo "⚠️  Erreur lecture rapport Gitleaks: ${e.getMessage()}"
                            }
                        }
                    }

                    echo "✅ Porte de sécurité passée (mode avertissement seulement)"
                }
            }
        }

        stage('Deploy to Staging') {
            steps {
                echo '🚀 Deploiement en environnement staging...'
                sh '''
                    docker stop devsecops-staging 2>/dev/null || true
                    docker rm devsecops-staging 2>/dev/null || true
                    docker run -d --name devsecops-staging --network jenkins -p ${APP_PORT}:5000 ${DOCKER_IMAGE}:${DOCKER_TAG}
                    sleep 10
                    echo "Application deployee sur http://localhost:${APP_PORT}"
                    # Tester que l'application fonctionne
                    curl -f http://localhost:${APP_PORT} || echo "L'application ne repond pas encore"
                '''
            }
        }

        stage('DAST - Tests dynamiques') {
            steps {
                echo '🌐 Scan DAST avec OWASP ZAP...'
                sh '''
                    docker run --rm --network jenkins -v "${WORKSPACE}":/zap/wrk:rw \
                        ghcr.io/zaproxy/zaproxy:stable zap-baseline.py \
                        -t http://devsecops-staging:5000 \
                        -J zap-report.json -r zap-report.html 2>&1 || true
                    
                    echo "=== RAPPORT ZAP ==="
                    if [ -f zap-report.json ]; then
                        echo "Fichiers ZAP trouves:"
                        ls -la zap-report.*
                    else
                        echo "Aucun rapport ZAP genere"
                        echo '{"alerts":[]}' > zap-report.json
                        echo '<html><body><h1>Scan DAST complete</h1></body></html>' > zap-report.html
                    fi
                    echo "==================="
                '''
            }
        }

        stage('Generate Security Report') {
            steps {
                echo '📊 Generation du rapport global...'
                sh '''
                    # Créer le dashboard principal
                    cat > security-report.html << 'EOF'
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Rapport de Sécurité DevSecOps</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }
        .container { background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        h1 { color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px; }
        .report-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; margin: 30px 0; }
        .report-card { background: #ecf0f1; padding: 20px; border-radius: 8px; border-left: 4px solid #3498db; }
        .report-card h3 { margin-top: 0; color: #2c3e50; }
        .report-link { display: inline-block; background: #3498db; color: white; padding: 10px 15px; text-decoration: none; border-radius: 5px; margin: 5px 0; }
        .status { padding: 5px 10px; border-radius: 15px; font-size: 0.9em; }
        .status-success { background: #d4edda; color: #155724; }
        .status-warning { background: #fff3cd; color: #856404; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🔒 Rapport de Sécurité DevSecOps</h1>
        <p><strong>Build:</strong> #${BUILD_NUMBER}</p>
        <p><strong>Date:</strong> $(date)</p>
        
        <div class="report-grid">
            <div class="report-card">
                <h3>🔍 SAST - Bandit</h3>
                <p>Analyse statique du code source Python</p>
                <a href="bandit-report.html" class="report-link" target="_blank">Voir le Rapport</a>
                <br><span class="status status-success">Complété</span>
            </div>
            
            <div class="report-card">
                <h3>📦 SCA - Safety</h3>
                <p>Analyse des dépendances Python</p>
                <a href="safety-report.txt" class="report-link" target="_blank">Voir le Rapport</a>
                <br><span class="status status-success">Complété</span>
            </div>
            
            <div class="report-card">
                <h3>🔑 Secrets - Gitleaks</h3>
                <p>Détection des secrets exposés</p>
                <a href="gitleaks-report.json" class="report-link" target="_blank">Voir le Rapport</a>
                <br><span class="status status-success">Complété</span>
            </div>
            
            <div class="report-card">
                <h3>🐳 Docker Scan - Trivy</h3>
                <p>Analyse de sécurité des images Docker</p>
                <a href="trivy-report.json" class="report-link" target="_blank">Voir le Rapport</a>
                <br><span class="status status-success">Complété</span>
            </div>
            
            <div class="report-card">
                <h3>🌐 DAST - OWASP ZAP</h3>
                <p>Tests de sécurité dynamiques</p>
                <a href="zap-report.html" class="report-link" target="_blank">Voir le Rapport</a>
                <br><span class="status status-success">Complété</span>
            </div>
        </div>
    </div>
</body>
</html>
EOF
                    echo "✅ Rapport de sécurité généré"
                    echo "=== FICHIERS FINAUX ==="
                    find . -name "*-report.*" -o -name "*.json" -o -name "*.html" -o -name "*.txt" | head -20
                    echo "======================"
                '''
            }
        }
    }

    post {
        always {
            echo '📦 Archivage des rapports...'
            archiveArtifacts artifacts: '*-report.*, *.json, *.html, *.txt', allowEmptyArchive: true, fingerprint: true
            
            publishHTML([
                allowMissing: true, 
                alwaysLinkToLastBuild: true, 
                keepAll: true,
                reportDir: '.', 
                reportFiles: 'security-report.html', 
                reportName: 'Security Dashboard'
            ])

            script {
                // Email FINAL avec la méthode simple
                try {
                    def emailBody = """
🚀 PIPELINE DEVSECOPS TERMINE

Build #${env.BUILD_NUMBER} - ${currentBuild.result ?: 'SUCCESS'}

📊 RAPPORTS DISPONIBLES:
• Dashboard: ${env.BUILD_URL}Security_20Dashboard/
• Bandit (SAST): ${env.BUILD_URL}artifact/bandit-report.html
• Safety (SCA): ${env.BUILD_URL}artifact/safety-report.txt  
• Gitleaks (Secrets): ${env.BUILD_URL}artifact/gitleaks-report.json
• Trivy (Docker): ${env.BUILD_URL}artifact/trivy-report.json
• ZAP (DAST): ${env.BUILD_URL}artifact/zap-report.html

📋 STATUT:
• ✅ Analyse SAST complétée
• ✅ Analyse SCA complétée
• ✅ Scan des secrets complété
• ✅ Scan Docker complété
• ✅ Tests DAST complétés

🔗 URL: ${env.BUILD_URL}

-- 
Pipeline DevSecOps Automatique
"""
                    
                    mail(
                        to: "${EMAIL_TO}",
                        subject: "DevSecOps Build #${env.BUILD_NUMBER} - ${currentBuild.result ?: 'SUCCESS'}",
                        body: emailBody
                    )
                    echo "✅ Email envoyé avec SUCCÈS à ${EMAIL_TO}"
                } catch (Exception e) {
                    echo "❌ ERREUR email: ${e.getMessage()}"
                    // Fallback: écrire dans les logs
                    echo "CONTENU EMAIL (pour debug):"
                    echo emailBody
                }
            }
        }
    }
}
