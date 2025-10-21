from flask import jsonify

from app.api import bp

@bp.route('/status', methods=['GET'])
def deployment_status_check():
    """
    Health check endpoint
    ---
    responses:
      200:
        description: Returns the status of the app
        examples:
          application/json: {"Message": "app up and running successfully"}
    """
    return jsonify({
        "Message": "app up and running successfully"
    })

