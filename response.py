"""
Common response class for whole project
"""


class Response:
    """
    Common response class for API response
    """

    @classmethod
    def success(cls, data, message):
        """
        Common success method for API response
        """
        return {"success": True, "data": data, "message": message}

    @classmethod
    def success_without_data(cls, message):
        """
        Common success_without_data method for API response
        """
        return {"success": True, "message": message}

    @classmethod
    def error(cls, error):
        """
        Common error method for API response
        """
        return {"success": False, "message": error}
