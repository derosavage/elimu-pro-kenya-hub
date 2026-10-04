from flask import jsonify


def ok(data=None, status=200, message=None, meta=None):
    body = {"success": True, "data": data}
    if message:
        body["message"] = message
    if meta:
        body["meta"] = meta
    return jsonify(body), status


def err(message, status=400, errors=None):
    body = {"success": False, "message": message}
    if errors:
        body["errors"] = errors
    return jsonify(body), status
