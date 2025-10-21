from flask import jsonify


class CustomError(Exception):
    def __init__(self, message=None, status=None, payload=None):
        super().__init__()
        self.message = message
        self.status = status
        self.payload = payload

    def to_dict(self):
        rv = dict(self.payload or ())
        rv.update({"message": self.message, "status": self.status})
        return rv


class NoContent(CustomError):
    def __init__(self, message="No data found."):
        super().__init__(message, 204)


class BadRequest(CustomError):
    def __init__(self, message="An issue occurred with the input data"):
        super().__init__(message, 400)


class Unauthorized(CustomError):
    def __init__(self, message="Please login and try again."):
        super().__init__(message, 401)


class Forbidden(CustomError):
    def __init__(self, message="You do not have the privilege to do this."):
        super().__init__(message, 403)


class InternalError(CustomError):
    def __init__(self, message="Please try again later."):
        super().__init__(message, 500)


class UnProcessable(CustomError):
    def __init__(self, message="The input format is wrong"):
        super().__init__(message, 422)


class Conflict(CustomError):
    def __init__(self, message="Duplicate Entry"):
        super().__init__(message, 409)


def handle_invalid_usage(error):
    response = jsonify(error.to_dict())
    response.status_code = 200
    return response
