# 🚀 Google Cloud Deployment Guide

This guide will help you **set up a FastAPI application** on **Google Cloud Run** using **Supabase** and **Docker**.

---

## 🎯 1. Create a Google Cloud Project  
If you haven't already, **create a Google Cloud Project** via the [Google Cloud Console](https://console.cloud.google.com/).

---

https://supabase.com/
add information from supabase to .env file

migrate db to supabase form migrations.sql

## 🛠 2. Setup Supabase
```sh
SUPABASE_URL="https://your-project.supabase.co"
SUPABASE_KEY="your-anon-or-service-role-key"
DATABASE_URL="postgresql://your-user:your-password@db.supabase.co:5432/postgres"
```

## ✅ 3. Enable required services

```sh
gcloud auth application-default login
gcloud config set project PROJECT-ID

gcloud services enable run.googleapis.com
gcloud services enable cloudbuild.googleapis.com
gcloud services enable artifactregistry.googleapis.com
```

---

## 🏗 4. Build & Push Docker Image  

### ✅ **Configure Project**  
```sh
gcloud config set project PROJECT-ID
```
### ✅ Create Docker Repository
```sh
gcloud artifacts repositories create fastapi-repo --repository-format=docker --location=europe-west6
```
### ✅ Authenticate Docker with GCP
```sh
gcloud auth configure-docker europe-west6-docker.pkg.dev
```
### ✅ Build Docker Image
```sh
docker build -t europe-west6-docker.pkg.dev/PROJECT-ID/fastapi-repo/fastapi-app .
```
### ✅ Push Docker Image
```sh
docker push europe-west6-docker.pkg.dev/PROJECT-ID/fastapi-repo/fastapi-app
```

---

## 🚀 5. Deploy to Cloud Run
### ✅ Deploy FastAPI Service
```sh
gcloud run deploy fastapi-service   --image europe-west6-docker.pkg.dev/PROJECT-ID/fastapi-repo/fastapi-app --platform managed --region europe-west6 --allow-unauthenticated
```
### ✅ Test Deployment
```sh
curl https://fastapi-service-xyz.a.run.app/api/health
```

---

## 🔄 6. Redeploy After Code Changes
### ✅ Rebuild Docker Image
```sh
docker build -t europe-west6-docker.pkg.dev/PROJECT-ID/fastapi-repo/fastapi-app .
```
### ✅ Push Updated Docker Image
```sh
docker push europe-west6-docker.pkg.dev/PROJECT-ID/fastapi-repo/fastapi-app
```
### ✅ Redeploy to Cloud Run
```sh
gcloud run deploy fastapi-service \
  --image europe-west6-docker.pkg.dev/PROJECT-ID/fastapi-repo/fastapi-app \
  --platform managed \
  --region europe-west6 \
  --allow-unauthenticated
```

---
## ✉️ 7. Email Setup (For Gmail Users)
If you're using Gmail for sending emails, generate a one-time App Password here. 2FA is required:

[Google App Passwords](https://myaccount.google.com/u/4/apppasswords?rapt=AEjHL4MfPuA8W6ucJrTHyMp0hBegBwgFoAdrjeNkrcFpR18luUk8JJnwAR-Uti-c0JazxBDpvXaI4wv_FIUhBK3IAp69A-yHAkmIQTq32OrGzWGuWDHk_zk&pageId=none&pli=1)

Use this App Password instead of your regular password in your `.env` file.



