from flask import Blueprint, request, jsonify
from app.services import events_service
events_bp = Blueprint('events', __name__)

@events_bp.get('/search')
async def search_events():
    query_name = request.args.get('name') 
    query_filter = request.args.get('filter')

    if not query_name:
        return jsonify({"error": "Missing 'name' query parameter"}), 400
    
    try:
        result = await events_service.find_event_details(query_name, query_filter)

        return jsonify(result), 200

    except Exception as e:
        return jsonify({"error": "Internal Server Error", "details": str(e)}), 500