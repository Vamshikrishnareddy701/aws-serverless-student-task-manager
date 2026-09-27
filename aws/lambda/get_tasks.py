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
    AWS Lambda Handler for GET /tasks endpoint.
    Retrieves tasks from Amazon DynamoDB with filtering & computes statistics.
    """
    if event.get("httpMethod") == "OPTIONS":
        return {"statusCode": 200, "headers": CORS_HEADERS, "body": ""}

    try:
        query_params = event.get("queryStringParameters") or {}
        status_filter = query_params.get("status")
        search_filter = query_params.get("search")
        priority_filter = query_params.get("priority")
        category_filter = query_params.get("category")

        table = get_table()
        response = table.scan()
        all_tasks = response.get("Items", [])

        filtered_tasks = all_tasks

        if status_filter:
            s_lower = status_filter.strip().lower()
            if s_lower == "completed":
                filtered_tasks = [t for t in filtered_tasks if t.get("completed") is True]
            elif s_lower == "pending":
                filtered_tasks = [t for t in filtered_tasks if t.get("completed") is False]

        if priority_filter and priority_filter.lower() != "all":
            filtered_tasks = [t for t in filtered_tasks if t.get("priority", "").lower() == priority_filter.strip().lower()]

        if category_filter:
            filtered_tasks = [t for t in filtered_tasks if t.get("category", "").lower() == category_filter.strip().lower()]

        if search_filter:
            q = search_filter.strip().lower()
            filtered_tasks = [
                t for t in filtered_tasks
                if q in t.get("title", "").lower() or q in t.get("description", "").lower()
            ]

        # Compute Statistics
        total = len(all_tasks)
        completed = sum(1 for t in all_tasks if t.get("completed") is True)
        pending = total - completed
        high_priority = sum(1 for t in all_tasks if t.get("priority") == "High" and not t.get("completed"))
        completion_rate = round((completed / total * 100), 1) if total > 0 else 0.0

        stats = {
            "total_tasks": total,
            "pending_tasks": pending,
            "completed_tasks": completed,
            "high_priority_tasks": high_priority,
            "completion_rate": completion_rate
        }

        # Sort tasks: pending first, high priority first, due date
        priority_weights = {"High": 1, "Medium": 2, "Low": 3}
        filtered_tasks.sort(
            key=lambda t: (
                1 if t.get("completed") else 0,
                priority_weights.get(t.get("priority"), 4),
                t.get("due_date") or "9999-12-31"
            )
        )

        return {
            "statusCode": 200,
            "headers": CORS_HEADERS,
            "body": json.dumps({
                "success": True,
                "count": len(filtered_tasks),
                "data": filtered_tasks,
                "stats": stats
            })
        }

    except Exception as e:
        print(f"Error fetching tasks: {str(e)}")
        return {
            "statusCode": 500,
            "headers": CORS_HEADERS,
            "body": json.dumps({"success": False, "error": f"Internal Server Error: {str(e)}"})
        }
