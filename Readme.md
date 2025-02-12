Ein google cloud projekt erstellen

Eine Cloud SQL db erstellen: api & services -> Cloud SQL Admin API (activate)

Gehe zum Tab Cloud SQL Console
1. create instance 
2. postgres SQL
3. sandbox (bc no need for high compute)
4. set instance id
5. local zone
6. strong pw
7. verbindungsname in .env-file 

Gehe zum Tab IAM und Service accounts
1. service accounts
2. keys, add key, create new key
3. json format
4. download json key
5. add location for key to .env file

Build und push image
0. configure:  gcloud config set project YOUR_PROJECT_ID
1. allow again: gcloud auth application-default login
2. Enable app registry to push image: gcloud services enable artifactregistry.googleapis.com
3. Docker repo in GCP: gcloud artifacts repositories create fastapi-repo --repository-format=docker --location=europe-west6
4. authenticate docker with gcp: gcloud auth configure-docker europe-west6-docker.pkg.dev
5. build: docker build -t europe-west6-docker.pkg.dev/YOUR_PROJECT_ID/fastapi-repo/fastapi-app .
6. push: docker push europe-west6-docker.pkg.dev/YOUR_PROJECT_ID/fastapi-repo/fastapi-app

Deploy to cloud run
1. gcloud services enable run.googleapis.com
2. gcloud run deploy fastapi-service --image europe-west6-docker.pkg.dev/YOUR_PROJECT_ID/fastapi-repo/fastapi-app --platform managed --region europe-west6 --allow-unauthenticated

Test: curl https://fastapi-service-xyz.a.run.app/api/health


Redeploy after changing code:
1. build: docker build -t europe-west6-docker.pkg.dev/YOUR_PROJECT_ID/fastapi-repo/fastapi-app .
2. push: docker push europe-west6-docker.pkg.dev/YOUR_PROJECT_ID/fastapi-repo/fastapi-app
3. gcloud run deploy fastapi-service --image europe-west6-docker.pkg.dev/YOUR_PROJECT_ID/fastapi-repo/fastapi-app --platform managed --region europe-west6 --allow-unauthenticated

for the email setup when using gmail use the following to generate a one time pw:
https://myaccount.google.com/u/4/apppasswords?rapt=AEjHL4MfPuA8W6ucJrTHyMp0hBegBwgFoAdrjeNkrcFpR18luUk8JJnwAR-Uti-c0JazxBDpvXaI4wv_FIUhBK3IAp69A-yHAkmIQTq32OrGzWGuWDHk_zk&pageId=none&pli=1


