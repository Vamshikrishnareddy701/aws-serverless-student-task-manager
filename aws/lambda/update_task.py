import json
import os
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
    AWS Lambda Handler for PUT /tasks/{id} endpoint.
    Updates an existing task in Amazon DynamoDB.
    """
    if event.get("httpMethod") == "OPTIONS":
        return {"statusCode": 200, "headers": CORS_HEADERS, "body": ""}

    try:
        path_params = event.get("pathParameters") or {}
        task_id = path_params.get("id")

        if not task_id:
            return {
                "statusCode": 400,
                "headers": CORS_HEADERS,
                "body": json.dumps({"success": False, "error": "Missing task ID in URL path"})
            }

        body_raw = event.get("body")
        if not body_raw:
            return {
                "statusCode": 400,
                "headers": CORS_HEADERS,
                "body": json.dumps({"success": False, "error": "Missing update payload"})
            }

        body = json.loads(body_raw) if isinstance(body_raw, str) else body_raw

        table = get_table()
        get_res = table.get_item(Key={"id": task_id})
        if "Item" not in get_res:
            return {
                "statusCode": 404,
                "headers": CORS_HEADERS,
                "body": json.dumps({"success": False, "error": f"Task with ID '{task_id}' not found"})
            }

        now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        update_expressions = ["#updated_at = :updated_at"]
        expression_names = {"#updated_at": "updated_at"}
        expression_values = {":updated_at": now_iso}

        if "title" in body and str(body["title"]).strip():
            update_expressions.append("#title = :title")
            expression_names["#title"] = "title"
            expression_values[":title"] = str(body["title"]).strip()

        if "description" in body:
            update_expressions.append("#description = :description")
            expression_names["#description"] = "description"
            expression_values[":description"] = str(body["description"]).strip()

        if "priority" in body and body["priority"] in ["Low", "Medium", "High"]:
            update_expressions.append("#priority = :priority")
            expression_names["#priority"] = "priority"
            expression_values[":priority"] = body["priority"]

        if "category" in body:
            update_expressions.append("#category = :category")
            expression_names["#category"] = "category"
            expression_values[":category"] = str(body["category"]).strip()

        if "due_date" in body:
            update_expressions.append("#due_date = :due_date")
            expression_names["#due_date"] = "due_date"
            expression_values[":due_date"] = str(body["due_date"]).strip()

        if "completed" in body:
            update_expressions.append("#completed = :completed")
            expression_names["#completed"] = "completed"
            expression_values[":completed"] = bool(body["completed"])

        update_query = "SET " + ", ".join(update_expressions)

        response = table.update_item(
            Key={"id": task_id},
            UpdateExpression=update_query,
            ExpressionAttributeNames=expression_names,
            ExpressionAttributeValues=expression_values,
            ReturnValues="ALL_NEW"
        )

        return {
            "statusCode": 200,
            "headers": CORS_HEADERS,
            "body": json.dumps({
                "success": True,
                "message": "Task updated successfully",
                "data": response.get("Attributes", {})
            })
        }

    except Exception as e:
        print(f"Error updating task: {str(e)}")
        return {
            "statusCode": 500,
            "headers": CORS_HEADERS,
            "body": json.dumps({"success": False, "error": f"Internal Server Error: {str(e)}"})
        }
