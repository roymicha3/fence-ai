import requests
from requests.exceptions import RequestException, HTTPError, ConnectionError, Timeout

class HttpClient:

    def __init__(self, base_url: str = ""):
        self.base_url = base_url.rstrip('/')

    def _full_url(self, path: str) -> str:
        if self.base_url:
            return f"{self.base_url}/{path.lstrip('/')}"
        return path

    def _handle_response(self, response: requests.Response) -> dict:
        """
        Handles the HTTP response, raising exceptions for bad status codes
        and returning JSON data if available.
        """
        try:
            response.raise_for_status() # Raises HTTPError for bad responses (4xx or 5xx)
            if response.headers.get('content-type', '').startswith('application/json'):
                return response.json()
            else:
                return {"message": "Request successful, but response is not JSON.", "content": response.text}
        except HTTPError as e:
            print(f"HTTP Error for URL {response.url}: {e.response.status_code} - {e.response.text}")
            raise
        except ValueError as e:
            print(f"Failed to decode JSON from response for URL {response.url}: {e}")
            raise
        except Exception as e:
            print(f"An unexpected error occurred while handling response: {e}")
            raise

    def _request(self, method: str, path: str, **kwargs) -> dict:
        """
        Internal helper method to execute HTTP requests and handle common errors.
        """
        url = self._full_url(path)
        try:
            # Use getattr to dynamically call the requests method (e.g., requests.get, requests.post)
            response = getattr(requests, method.lower())(url, **kwargs)
            print(f"{method.upper()} {url} - Status: {response.status_code}")
            return self._handle_response(response)
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