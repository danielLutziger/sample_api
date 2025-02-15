# 🚀 Google Cloud Deployment Guide

This guide will help you **set up a FastAPI application** on **Google Cloud Run** using **Supabase** and **Docker**.

---

## 🎯 1. Create a Google Cloud Project  
If you haven't already, **create a Google Cloud Project** via the [Google Cloud Console](https://console.cloud.google.com/).

---
https://supabase.com/
add information from supabase to .env file
migrate db to supabase

## 🛠 2. Setup Cloud SQL Database  

### ✅ Enable Cloud SQL API  
- Go to **Google Cloud Console** → **APIs & Services**  
- Enable **Cloud SQL Admin API**  

```sh
gcloud auth application-default login
```

```sh
gcloud config set project fast-aloe
```

```sh
gcloud services enable run.googleapis.com
gcloud services enable cloudbuild.googleapis.com
gcloud services enable artifactregistry.googleapis.com
gcloud services enable sqladmin.googleapis.com
gcloud services enable compute.googleapis.com
```

### ✅ Create a Cloud SQL Instance  
1. Navigate to **Cloud SQL Console**  
2. Click **"Create Instance"**  
3. Choose **PostgreSQL**  
4. Select **Sandbox** (No need for high compute)  
5. Set an **Instance ID**  
6. Choose a **Local Zone**  
7. Set a **Strong Password**  
8. Copy the **Connection Name** and add it to your `.env` file  

---

## 🔑 3. Setup IAM & Service Accounts  

### ✅ Create a Service Account & Key  
1. Navigate to **IAM & Admin** → **Service Accounts**  
2. Click on **"Create Service Account"**  
3. Go to the **"Keys"** tab → Click **"Add Key"** → **Create New Key**  
4. Choose **JSON format** and **Download the key**  
5. Add the **path to the key** in your `.env` file  

---

gcloud projects add-iam-policy-binding fast-aloe --member="serviceAccount:fast-aloe@appspot.gserviceaccount.com" --role="roles/cloudsql.client"


## 🏗 4. Build & Push Docker Image  

### ✅ **Configure Project**  
```sh
gcloud config set project fast-aloe
```
### ✅ Authenticate
```sh
gcloud auth application-default login
```
### ✅ Enable Artifact Registry
```sh
gcloud services enable artifactregistry.googleapis.com
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
docker build -t europe-west6-docker.pkg.dev/fast-aloe/fastapi-repo/fastapi-app .
```
### ✅ Push Docker Image
```sh
docker push europe-west6-docker.pkg.dev/fast-aloe/fastapi-repo/fastapi-app
```

---

## 🚀 5. Deploy to Cloud Run
### ✅ Enable Cloud Run API
```sh
gcloud services enable run.googleapis.com
```
### ✅ Deploy FastAPI Service
```sh
gcloud run deploy fastapi-service   --image europe-west6-docker.pkg.dev/fast-aloe/fastapi-repo/fastapi-app --platform managed --region europe-west6 --allow-unauthenticated
```
### ✅ Test Deployment
```sh
curl https://fastapi-service-xyz.a.run.app/api/health
```

---

## 🔄 6. Redeploy After Code Changes
### ✅ Rebuild Docker Image
```sh
docker build -t europe-west6-docker.pkg.dev/fast-aloe/fastapi-repo/fastapi-app .
```
### ✅ Push Updated Docker Image
```sh
docker push europe-west6-docker.pkg.dev/fast-aloe/fastapi-repo/fastapi-app
```
### ✅ Redeploy to Cloud Run
```sh
gcloud run deploy fastapi-service \
  --image europe-west6-docker.pkg.dev/fast-aloe/fastapi-repo/fastapi-app \
  --platform managed \
  --region europe-west6 \
  --allow-unauthenticated
```

---
## ✉️ 7. Email Setup (For Gmail Users)
If you're using Gmail for sending emails, generate a one-time App Password here. 2FA is required:

[Google App Passwords](https://myaccount.google.com/u/4/apppasswords?rapt=AEjHL4MfPuA8W6ucJrTHyMp0hBegBwgFoAdrjeNkrcFpR18luUk8JJnwAR-Uti-c0JazxBDpvXaI4wv_FIUhBK3IAp69A-yHAkmIQTq32OrGzWGuWDHk_zk&pageId=none&pli=1)

Use this App Password instead of your regular password in your `.env` file.



