pipeline {
  agent any
  options { timestamps(); skipDefaultCheckout(true) }
  triggers { pollSCM('H/2 * * * *') }
  environment { SMOKE_BASE_URL = 'http://host.docker.internal:8080' }
  stages {
    stage('Checkout') {
      steps {
        checkout scm
        script { env.TAG = sh(returnStdout: true, script: 'git rev-parse --short=7 HEAD').trim() }
      }
    }
    stage('Build') { steps { sh 'bash scripts/build_all.sh "$TAG"' } }
    stage('Push') { steps { sh 'bash scripts/push_images.sh "$TAG"' } }
    stage('Deploy') {
      steps {
        withCredentials([file(credentialsId: 'kubeconfig', variable: 'KUBECONFIG')]) {
          sh 'bash scripts/deploy.sh "$TAG"'
        }
      }
    }
    stage('Smoke') {
      steps {
        withCredentials([file(credentialsId: 'kubeconfig', variable: 'KUBECONFIG')]) {
          sh 'bash scripts/smoke_test.sh'
        }
      }
    }
  }
}
