import json
import os
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
    AWS Lambda Handler for DELETE /tasks/{id} endpoint.
    Deletes a task from Amazon DynamoDB.
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

        table = get_table()
        get_res = table.get_item(Key={"id": task_id})
        if "Item" not in get_res:
            return {
                "statusCode": 404,
                "headers": CORS_HEADERS,
                "body": json.dumps({"success": False, "error": f"Task with ID '{task_id}' not found"})
            }

        table.delete_item(Key={"id": task_id})

        return {
            "statusCode": 200,
            "headers": CORS_HEADERS,
            "body": json.dumps({
                "success": True,
                "message": f"Task '{task_id}' deleted successfully",
                "deleted_id": task_id
            })
        }

    except Exception as e:
        print(f"Error deleting task: {str(e)}")
        return {
            "statusCode": 500,
            "headers": CORS_HEADERS,
            "body": json.dumps({"success": False, "error": f"Internal Server Error: {str(e)}"})
        }
