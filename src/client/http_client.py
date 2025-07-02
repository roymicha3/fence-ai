import requests
from requests.exceptions import RequestException, HTTPError, ConnectionError, Timeout

class HttpClient:

    def __init__(self, base_url: str = ""):
        self.base_url = base_url.rstrip('/')

    def _full_url(self, path: str) -> str:
        if self.base_url:
            return f"{self.base_url}/{path.lstrip('/')}"
        return path

    def _handle_response(self, response: requests.Response, allow_error_codes=None) -> dict:
        """
        Handles the HTTP response, raising exceptions for bad status codes
        and returning JSON data if available.
        
        Args:
            response: The HTTP response to handle
            allow_error_codes: Optional list of HTTP status codes to handle gracefully
                             instead of raising an exception
        """
        # Special handling for specific error codes
        if allow_error_codes is None:
            allow_error_codes = []
            
        # Handle webhook endpoints specially - if URL contains 'webhook', treat 404 as non-fatal during development
        if 'webhook' in response.url.lower() and response.status_code == 404:
            allow_error_codes.append(404)
            
        try:
            # Handle allowed error codes gracefully
            if response.status_code in allow_error_codes:
                error_message = f"HTTP {response.status_code} error allowed: {response.reason}"
                print(f"Note: {error_message}")
                try:
                    # Try to parse error response as JSON
                    error_data = response.json()
                    return {
                        "success": False,
                        "error": error_message,
                        "error_data": error_data,
                        "status_code": response.status_code
                    }
                except ValueError:
                    # If not JSON, return the text content
                    return {
                        "success": False,
                        "error": error_message,
                        "content": response.text,
                        "status_code": response.status_code
                    }
            
            # For all other status codes, use standard handling
            response.raise_for_status() # Raises HTTPError for bad responses (4xx or 5xx)
            
            # Check if response is empty
            if not response.text.strip():
                return {"message": "Request successful, but response is empty.", "success": True, "empty": True}
                
            # Try to parse as JSON if content-type indicates JSON or attempt to parse anyway
            if response.headers.get('content-type', '').startswith('application/json'):
                try:
                    return response.json()
                except ValueError as e:
                    # If JSON parsing fails, return a structured error response instead of raising
                    print(f"Failed to decode JSON from response for URL {response.url}: {e}")
                    return {
                        "success": False,
                        "error": f"Failed to decode JSON: {str(e)}",
                        "content": response.text,
                        "status_code": response.status_code
                    }
            else:
                return {"message": "Request successful, but response is not JSON.", "content": response.text}
        except HTTPError as e:
            print(f"HTTP Error for URL {response.url}: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            print(f"An unexpected error occurred while handling response: {e}")
            raise

    def _request(self, method: str, path: str, allow_error_codes=None, **kwargs) -> dict:
        """
        Internal helper method to execute HTTP requests and handle common errors.
        
        Args:
            method: HTTP method to use (e.g., 'GET', 'POST')
            path: URL path to request
            allow_error_codes: Optional list of HTTP status codes to handle gracefully
            **kwargs: Additional arguments to pass to the request method
        """
        url = self._full_url(path)
        try:
            # Use getattr to dynamically call the requests method (e.g., requests.get, requests.post)
            response = getattr(requests, method.lower())(url, **kwargs)
            print(f"{method.upper()} {url} - Status: {response.status_code}")
            return self._handle_response(response, allow_error_codes=allow_error_codes)
        except ConnectionError as e:
            print(f"Connection Error for {method.upper()} {url}: {e}")
            raise
        except Timeout as e:
            print(f"Timeout Error for {method.upper()} {url}: {e}")
            raise
        except RequestException as e:
            print(f"An unexpected Request Error occurred for {method.upper()} {url}: {e}")
            raise

    def get(self, path: str, params: dict = None, headers: dict = None, timeout: int = 30) -> dict:
        """Sends a GET request."""
        return self._request("GET", path, params=params, headers=headers, timeout=timeout)

    def post(self, path: str, json_data: dict = None, data: dict = None, headers: dict = None, timeout: int = 30) -> dict:
        """Sends a POST request."""
        return self._request("POST", path, json=json_data, data=data, headers=headers, timeout=timeout)

    def put(self, path: str, json_data: dict = None, data: dict = None, headers: dict = None, timeout: int = 30) -> dict:
        """Sends a PUT request."""
        return self._request("PUT", path, json=json_data, data=data, headers=headers, timeout=timeout)

    def delete(self, path: str, params: dict = None, headers: dict = None, timeout: int = 30) -> dict:
        """Sends a DELETE request."""
        return self._request("DELETE", path, params=params, headers=headers, timeout=timeout)