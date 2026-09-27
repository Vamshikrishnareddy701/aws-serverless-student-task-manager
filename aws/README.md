# ☁️ AWS Serverless Deployment Guide

This document provides complete, step-by-step instructions for deploying the **AWS Serverless Student Task Manager** onto Amazon Web Services (AWS) using production-grade serverless components.

---

## 🏗️ Architecture Overview

```mermaid
graph TD
    User([🌐 Student Browser]) -->|HTTPS Static Content| S3[📦 Amazon S3 Bucket\nStatic Website Hosting]
    User -->|REST API Requests| APIGW[⚡ Amazon API Gateway\nHTTP / REST API]
    
    APIGW -->|POST /tasks| L1[λ Lambda: create_task]
    APIGW -->|GET /tasks| L2[λ Lambda: get_tasks]
    APIGW -->|PUT /tasks/{id}| L3[λ Lambda: update_task]
    APIGW -->|DELETE /tasks/{id}| L4[λ Lambda: delete_task]
    
    L1 -->|PutItem| DDB[(🗄️ Amazon DynamoDB\nTable: StudentTasks)]
    L2 -->|Scan / Query| DDB
    L3 -->|UpdateItem| DDB
    L4 -->|DeleteItem| DDB
    
    L1 -.->|Logs & Metrics| CW[📊 Amazon CloudWatch]
    L2 -.->|Logs & Metrics| CW
    L3 -.->|Logs & Metrics| CW
    L4 -.->|Logs & Metrics| CW
```

---

## 🚀 Step-by-Step Deployment Instructions

### Step 1: Create Amazon DynamoDB Table
1. Open the **AWS Management Console** and navigate to **DynamoDB**.
2. Click **Create table**.
3. Configure the table:
   - **Table name**: `StudentTasks`
   - **Partition key**: `id` (String)
   - **Table class**: DynamoDB Standard
   - **Read/Write capacity mode**: On-demand (Pay-per-request)
4. Click **Create table**.

---

### Step 2: Create IAM Execution Role for Lambda
1. Navigate to **AWS IAM** > **Roles** > **Create role**.
2. Select **AWS service** as Trusted Entity, then select **Lambda**.
3. Attach the following managed policies:
   - `AWSLambdaBasicExecutionRole` (for CloudWatch Logs)
   - `AmazonDynamoDBFullAccess` (or create a custom least-privilege inline policy for `StudentTasks` table)
4. Name the role: `StudentTaskManagerLambdaRole` and click **Create role**.

---

### Step 3: Deploy AWS Lambda Functions
Navigate to **AWS Lambda** > **Create function** for each of the 4 endpoints:

| Function Name | Handler | Source File | Description |
|---|---|---|---|
| `StudentTask_Create` | `create_task.lambda_handler` | `aws/lambda/create_task.py` | Handles POST /tasks |
| `StudentTask_Get` | `get_tasks.lambda_handler` | `aws/lambda/get_tasks.py` | Handles GET /tasks |
| `StudentTask_Update` | `update_task.lambda_handler` | `aws/lambda/update_task.py` | Handles PUT /tasks/{id} |
| `StudentTask_Delete` | `delete_task.lambda_handler` | `aws/lambda/delete_task.py` | Handles DELETE /tasks/{id} |

**For each function:**
1. Choose **Python 3.12** runtime.
2. Under Permissions, assign `StudentTaskManagerLambdaRole`.
3. Paste the code from the corresponding file in `aws/lambda/`.
4. Add an Environment Variable:
   - Key: `TABLE_NAME` | Value: `StudentTasks`

---

### Step 4: Configure Amazon API Gateway
1. Navigate to **Amazon API Gateway** > **Create API**.
2. Choose **HTTP API** (or REST API) and click **Build**.
3. Add integrations for each Lambda function:
   - `POST /tasks` -> `StudentTask_Create`
   - `GET /tasks` -> `StudentTask_Get`
   - `GET /health` -> `StudentTask_Get`
   - `PUT /tasks/{id}` -> `StudentTask_Update`
   - `DELETE /tasks/{id}` -> `StudentTask_Delete`
4. Configure **CORS**:
   - **Access-Control-Allow-Origin**: `*`
   - **Access-Control-Allow-Headers**: `Content-Type, Authorization, X-Api-Key`
   - **Access-Control-Allow-Methods**: `GET, POST, PUT, DELETE, OPTIONS`
5. Deploy API to `$default` or `prod` stage and copy the Invoke URL (e.g., `https://abc123xyz.execute-api.us-east-1.amazonaws.com`).

---

### Step 5: Deploy Frontend to Amazon S3
1. Navigate to **Amazon S3** > **Create bucket**.
2. Name the bucket (e.g., `student-task-manager-app`).
3. Enable **Static website hosting** under Bucket Properties:
   - Index document: `index.html`
4. Update `frontend/script.js` so `API_BASE_URL` points to your API Gateway Invoke URL:
   ```javascript
   const API_BASE_URL = 'https://abc123xyz.execute-api.us-east-1.amazonaws.com/api';
   ```
5. Upload `index.html`, `style.css`, and `script.js` to the bucket.
6. Add bucket policy for public read access:
   ```json
   {
     "Version": "2012-10-17",
     "Statement": [
       {
         "Sid": "PublicReadGetObject",
         "Effect": "Allow",
         "Principal": "*",
         "Action": "s3:GetObject",
         "Resource": "arn:aws:s3:::student-task-manager-app/*"
       }
     ]
   }
   ```

---

### Step 6: Amazon CloudWatch Monitoring
- **Log Groups**: Each Lambda function automatically logs execution metrics, print statements, and errors under `/aws/lambda/StudentTask_*`.
- **Metrics**: Monitor `Invocations`, `Duration`, `Errors`, and `Throttles` in CloudWatch Dashboards.
