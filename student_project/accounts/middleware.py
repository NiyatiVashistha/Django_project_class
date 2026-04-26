import time
import logging

class ExecutionTimingMiddleware:
    """
    EDUCATIONAL FEATURE: Django Middleware
    Middleware is a framework of hooks into Django's request/response processing.
    It's a light, low-level "plugin" system for globally altering Django's input or output.
    
    This middleware calculates how long a request took to process and adds it as a header
    `X-Execution-Time` on the HTTP Response!
    """
    
    def __init__(self, get_response):
        # One-time configuration and initialization when the Web Server starts.
        self.get_response = get_response
        self.logger = logging.getLogger(__name__)

    def __call__(self, request):
        # Code to be executed for each request BEFORE the view (and later middleware) are called.
        start_time = time.time()

        # The `get_response` call actually passes the request to the next middleware
        # and eventually to the view!
        response = self.get_response(request)

        # Code to be executed for each request/response AFTER the view is called.
        duration = time.time() - start_time
        
        # Add a custom HTTP header to the response that the frontend can read!
        response['X-Execution-Time'] = str(duration)
        
        # Uncomment below to print to the development server console:
        # print(f"[{request.method}] {request.path} took {duration:.4f} seconds")

        return response