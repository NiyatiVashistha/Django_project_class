import time
import logging
import ipaddress
from django.conf import settings
from django.core.exceptions import PermissionDenied

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
        
        return response


class AdminHostRestrictionMiddleware:
    """
    SECURITY FEATURE: Restricts access to the /admin/ URL to only allowed hosts.
    This ensures that even if someone knows the admin URL, they can't access it 
    unless they are connecting from a specific 'Management' host or VPN.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path.startswith('/admin/'):
            # Allow all hosts in DEBUG mode for development ease
            if settings.DEBUG:
                return self.get_response(request)

            allowed_hosts = getattr(settings, 'ADMIN_ALLOWED_HOSTS', [])
            current_host = request.get_host().split(':')[0] # Remove port if present

            is_allowed = False
            for entry in allowed_hosts:
                # Exact match
                if entry == current_host:
                    is_allowed = True
                    break
                # CIDR match
                try:
                    if '/' in entry:
                        network = ipaddress.ip_network(entry)
                        ip_addr = ipaddress.ip_address(current_host)
                        if ip_addr in network:
                            is_allowed = True
                            break
                except (ValueError, AttributeError):
                    continue
            
            if not is_allowed:
                raise PermissionDenied("Admin portal is restricted to management hosts.")
                
        return self.get_response(request)