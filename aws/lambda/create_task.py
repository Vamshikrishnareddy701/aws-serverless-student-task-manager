import json
import os
import uuid
from datetime import datetime, timezone
import boto3

CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "Content-Type,Authorization,X-Amz-Date,X-Api-Key,X-Amz-Security-Token",
    "Access-Control-Allow-Methods": "OPTIONS,POST,GET,PUT,DELETE"
}


def get_table():
    """Lazily initializes DynamoDB Table resource."""
    table_name = os.environ.get("TABLE_NAME", "StudentTasks")
    region_name = os.environ.get("AWS_DEFAULT_REGION", "us-east-1")
    dynamodb = boto3.resource("dynamodb", region_name=region_name)
    return dynamodb.Table(table_name)


def lambda_handler(event, context):
    """
    AWS Lambda Handler for POST /tasks endpoint.
    Creates a new student task in Amazon DynamoDB.
    """
    if event.get("httpMethod") == "OPTIONS":
        return {"statusCode": 200, "headers": CORS_HEADERS, "body": ""}

    try:
        body_raw = event.get("body")
        if not body_raw:
            return {
                "statusCode": 400,
                "headers": CORS_HEADERS,
                "body": json.dumps({"success": False, "error": "Missing request payload"})
            }

        body = json.loads(body_raw) if isinstance(body_raw, str) else body_raw

        title = body.get("title")
        if not title or not str(title).strip():
            return {
                "statusCode": 400,
                "headers": CORS_HEADERS,
                "body": json.dumps({"success": False, "error": "Validation Error: Task title is required"})
            }

        task_id = f"task_{uuid.uuid4().hex[:8]}"
        now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        task_item = {
            "id": task_id,
            "title": str(title).strip(),
            "description": str(body.get("description", "")).strip(),
            "priority": body.get("priority", "Medium") if body.get("priority") in ["Low", "Medium", "High"] else "Medium",
            "category": str(body.get("category", "General")).strip(),
            "due_date": str(body.get("due_date", "")).strip(),
            "completed": False,
            "created_at": now_iso,
            "updated_at": now_iso
        }

        table = get_table()
        table.put_item(Item=task_item)

        return {
            "statusCode": 201,
            "headers": CORS_HEADERS,
            "body": json.dumps({
                "success": True,
                "message": "Task created successfully",
                "data": task_item
            })
        }

    except Exception as e:
        print(f"Error creating task: {str(e)}")
        return {
            "statusCode": 500,
            "headers": CORS_HEADERS,
            "body": json.dumps({"success": False, "error": f"Internal Server Error: {str(e)}"})
        }
