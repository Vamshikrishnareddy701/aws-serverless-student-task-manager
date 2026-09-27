"""
Local AWS Lambda & DynamoDB Test Suite.

Uses 'moto' to mock Amazon DynamoDB in-memory. Allows testing exact AWS Lambda
handler functions and boto3 DynamoDB operations locally without an active AWS account,
AWS credentials, or cloud charges.
"""

import json
import os
import sys
import boto3
from moto import mock_aws

# Add lambda directory to Python search path
lambda_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(lambda_dir, "lambda"))

# Import AWS Lambda Handlers
from create_task import lambda_handler as create_handler
from get_tasks import lambda_handler as get_handler
from update_task import lambda_handler as update_handler
from delete_task import lambda_handler as delete_handler


@mock_aws
def run_local_lambda_tests():
    """Executes full CRUD test cycle against mock DynamoDB in-memory."""
    # Set dummy AWS credentials & region for boto3 mock
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_SECURITY_TOKEN"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"
    os.environ["AWS_DEFAULT_REGION"] = "us-east-1"
    os.environ["TABLE_NAME"] = "StudentTasks"

    print("==================================================================")
    print(" AWS LAMBDA & DYNAMODB LOCAL IN-MEMORY TEST SUITE")
    print("==================================================================")

    # 1. Initialize Mock DynamoDB Table
    dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
    table_name = "StudentTasks"
    
    print(f"\n[1/6] Creating mock DynamoDB Table '{table_name}'...")
    dynamodb.create_table(
        TableName=table_name,
        KeySchema=[{"AttributeName": "id", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "id", "AttributeType": "S"}],
        BillingMode="PAY_PER_REQUEST"
    )
    print(" -> Table 'StudentTasks' created successfully in-memory.")

    # 2. Test create_task Lambda Handler (POST /tasks)
    print("\n[2/6] Testing 'create_task.py' Lambda Handler...")
    create_event_1 = {
        "httpMethod": "POST",
        "body": json.dumps({
            "title": "Study AWS Lambda & DynamoDB Integrations",
            "description": "Learn event structure and boto3 table methods.",
            "priority": "High",
            "category": "Exam",
            "due_date": "2026-10-15"
        })
    }
    res_create_1 = create_handler(create_event_1, None)
    print(" -> Create Task Status:", res_create_1["statusCode"])
    assert res_create_1["statusCode"] == 201
    
    body_1 = json.loads(res_create_1["body"])
    task_id_1 = body_1["data"]["id"]
    print(f" -> Created Task ID: {task_id_1} (Title: '{body_1['data']['title']}')")

    # Create a second task
    create_event_2 = {
        "httpMethod": "POST",
        "body": json.dumps({
            "title": "Complete Capstone Cloud Architecture Diagram",
            "description": "Draw S3 -> API Gateway -> Lambda -> DynamoDB flow.",
            "priority": "Medium",
            "category": "Project",
            "due_date": "2026-10-20"
        })
    }
    res_create_2 = create_handler(create_event_2, None)
    assert res_create_2["statusCode"] == 201
    task_id_2 = json.loads(res_create_2["body"])["data"]["id"]

    # 3. Test get_tasks Lambda Handler (GET /tasks)
    print("\n[3/6] Testing 'get_tasks.py' Lambda Handler...")
    get_event = {
        "httpMethod": "GET",
        "queryStringParameters": None
    }
    res_get = get_handler(get_event, None)
    print(" -> Get Tasks Status:", res_get["statusCode"])
    assert res_get["statusCode"] == 200

    get_body = json.loads(res_get["body"])
    print(f" -> Retreived Task Count: {get_body['count']}")
    print(f" -> Statistics: {get_body['stats']}")
    assert get_body["count"] == 2
    assert get_body["stats"]["total_tasks"] == 2

    # 4. Test update_task Lambda Handler (PUT /tasks/{id})
    print("\n[4/6] Testing 'update_task.py' Lambda Handler...")
    update_event = {
        "httpMethod": "PUT",
        "pathParameters": {"id": task_id_1},
        "body": json.dumps({
            "completed": True,
            "description": "Updated description via local Lambda test."
        })
    }
    res_update = update_handler(update_event, None)
    print(" -> Update Task Status:", res_update["statusCode"])
    assert res_update["statusCode"] == 200
    
    update_body = json.loads(res_update["body"])
    assert update_body["data"]["completed"] is True
    print(f" -> Task '{task_id_1}' marked completed.")

    # 5. Test delete_task Lambda Handler (DELETE /tasks/{id})
    print("\n[5/6] Testing 'delete_task.py' Lambda Handler...")
    delete_event = {
        "httpMethod": "DELETE",
        "pathParameters": {"id": task_id_2}
    }
    res_delete = delete_handler(delete_event, None)
    print(" -> Delete Task Status:", res_delete["statusCode"])
    assert res_delete["statusCode"] == 200
    print(f" -> Task '{task_id_2}' deleted successfully.")

    # 6. Verify final state with get_tasks
    print("\n[6/6] Verifying final table state after deletion...")
    res_final_get = get_handler(get_event, None)
    final_body = json.loads(res_final_get["body"])
    print(f" -> Final Task Count: {final_body['count']} (Expected: 1)")
    assert final_body["count"] == 1
    assert final_body["stats"]["completed_tasks"] == 1
    assert final_body["stats"]["pending_tasks"] == 0

    print("\n==================================================================")
    print(" SUCCESS: ALL 4 AWS LAMBDA HANDLERS PASSED LOCAL DYNAMODB TESTS!")
    print("==================================================================")


if __name__ == "__main__":
    run_local_lambda_tests()
