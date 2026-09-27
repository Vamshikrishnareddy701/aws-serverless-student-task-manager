"""
AWS Serverless Student Task Manager - Local Flask Backend API Server.

Serves RESTful endpoints for student task management and hosts the local
frontend static interface for seamless local development & testing.
"""

import os
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from database import get_db

# Initialize Flask App
base_dir = os.path.dirname(os.path.abspath(__file__))
frontend_dir = os.path.abspath(os.path.join(base_dir, "..", "frontend"))

app = Flask(__name__, static_folder=frontend_dir, static_url_path="")
CORS(app)  # Enable Cross-Origin Resource Sharing for API requests

# Database Instance
db = get_db()


# -----------------------------------------------------------------------------
# Frontend Static Routing
# -----------------------------------------------------------------------------
@app.route("/")
def serve_frontend():
    """Serves the main frontend index.html page."""
    return send_from_directory(frontend_dir, "index.html")


@app.route("/<path:path>")
def serve_static_files(path):
    """Serves static frontend assets (css, js, images)."""
    if os.path.exists(os.path.join(frontend_dir, path)):
        return send_from_directory(frontend_dir, path)
    return send_from_directory(frontend_dir, "index.html")


# -----------------------------------------------------------------------------
# REST API Endpoints
# -----------------------------------------------------------------------------

@app.route("/api/health", methods=["GET"])
def health_check():
    """System health check endpoint for monitoring."""
    return jsonify({
        "status": "healthy",
        "service": "AWS Serverless Student Task Manager - Local API",
        "database": "JSON File Persistence (Local Mock)"
    }), 200


@app.route("/api/tasks", methods=["GET"])
def get_tasks():
    """
    GET /api/tasks
    Retrieve all tasks with optional status, search, priority, or category filters.
    """
    try:
        status = request.args.get("status")
        search = request.args.get("search")
        priority = request.args.get("priority")
        category = request.args.get("category")

        tasks = db.get_all_tasks(
            status=status,
            search=search,
            priority=priority,
            category=category
        )
        stats = db.get_statistics()

        return jsonify({
            "success": True,
            "count": len(tasks),
            "data": tasks,
            "stats": stats
        }), 200

    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"Failed to fetch tasks: {str(e)}"
        }), 500


@app.route("/api/tasks/<task_id>", methods=["GET"])
def get_task_by_id(task_id):
    """
    GET /api/tasks/<id>
    Retrieve a specific task by ID.
    """
    try:
        task = db.get_task_by_id(task_id)
        if not task:
            return jsonify({
                "success": False,
                "error": f"Task with ID '{task_id}' not found"
            }), 404

        return jsonify({
            "success": True,
            "data": task
        }), 200

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route("/api/tasks", methods=["POST"])
def create_task():
    """
    POST /api/tasks
    Create a new student task.
    Required JSON body: { "title": string }
    Optional JSON body: { "description", "priority", "due_date", "category" }
    """
    try:
        data = request.get_json(silent=True)
        if not data:
            return jsonify({
                "success": False,
                "error": "Invalid request payload. Request body must be valid JSON."
            }), 400

        title = data.get("title")
        if not title or not str(title).strip():
            return jsonify({
                "success": False,
                "error": "Validation Error: Task title is required."
            }), 400

        description = data.get("description", "")
        priority = data.get("priority", "Medium")
        due_date = data.get("due_date", "")
        category = data.get("category", "General")

        new_task = db.create_task(
            title=title,
            description=description,
            priority=priority,
            due_date=due_date,
            category=category
        )

        return jsonify({
            "success": True,
            "message": "Task created successfully",
            "data": new_task
        }), 201

    except ValueError as ve:
        return jsonify({"success": False, "error": str(ve)}), 400
    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"Failed to create task: {str(e)}"
        }), 500


@app.route("/api/tasks/<task_id>", methods=["PUT"])
def update_task(task_id):
    """
    PUT /api/tasks/<id>
    Update an existing task or toggle completion status.
    """
    try:
        data = request.get_json(silent=True)
        if not data:
            return jsonify({
                "success": False,
                "error": "Invalid request payload. Request body must be valid JSON."
            }), 400

        updated_task = db.update_task(task_id, data)
        if not updated_task:
            return jsonify({
                "success": False,
                "error": f"Task with ID '{task_id}' not found"
            }), 404

        return jsonify({
            "success": True,
            "message": "Task updated successfully",
            "data": updated_task
        }), 200

    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"Failed to update task: {str(e)}"
        }), 500


@app.route("/api/tasks/<task_id>", methods=["DELETE"])
def delete_task(task_id):
    """
    DELETE /api/tasks/<id>
    Delete a task by ID.
    """
    try:
        success = db.delete_task(task_id)
        if not success:
            return jsonify({
                "success": False,
                "error": f"Task with ID '{task_id}' not found"
            }), 404

        return jsonify({
            "success": True,
            "message": f"Task '{task_id}' deleted successfully",
            "deleted_id": task_id
        }), 200

    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"Failed to delete task: {str(e)}"
        }), 500


@app.route("/api/stats", methods=["GET"])
def get_stats():
    """
    GET /api/stats
    Get dashboard task statistics.
    """
    try:
        stats = db.get_statistics()
        return jsonify({
            "success": True,
            "data": stats
        }), 200
    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"Failed to compute statistics: {str(e)}"
        }), 500


@app.route("/api/seed", methods=["POST"])
def seed_data():
    """
    POST /api/seed
    Resets/seeds default dataset for demo purposes.
    """
    try:
        db.seed_defaults()
        tasks = db.get_all_tasks()
        return jsonify({
            "success": True,
            "message": "Default student tasks reset successfully",
            "data": tasks
        }), 200
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


# Start local server if run directly
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print("=" * 65)
    print(" AWS SERVERLESS STUDENT TASK MANAGER - LOCAL DEV SERVER")
    print("=" * 65)
    print(f" Frontend Interface:  http://localhost:{port}/")
    print(f" API Health Endpoint: http://localhost:{port}/api/health")
    print(f" REST Tasks Endpoint: http://localhost:{port}/api/tasks")
    print("=" * 65)
    app.run(host="0.0.0.0", port=port, debug=True)

