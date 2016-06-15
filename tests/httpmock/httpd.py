# Copyright (C) 2016 O.S. Systems Software LTDA.
# This software is released under the MIT License

import threading
from functools import wraps
from http.server import BaseHTTPRequestHandler, HTTPServer


class Request(object):

    def __init__(self, request):
        addr, port = request.server.server_address
        self.url = 'http://{}:{}{}'.format(addr, port, request.path)
        self.method = request.command
        self.headers = request.headers
        content_length = int(self.headers.get('Content-length', 0))
        self.body = request.rfile.read(content_length)


class Response(object):

    def __init__(self, status_code, headers, body=None):
        self.status_code = status_code
        self.headers = headers
        self.body = body


class RequestHandler(BaseHTTPRequestHandler):
    '''
    This class is responsible for returning pre registered responses.

    It is able to return a 404 if there is no response registered for
    a given request. Also, it responds a 405 if a method is not
    allowed in a given path.

    It supports request history and even if a request is not
    successful (eg. when you get 404 or 405) it will be storaged. In
    this way it is easy to debug if your code is making the right
    request.

    Finally, there is a reset method that deletes all registered
    responses and saved requests in history. It is useful for setting
    up and down tests.
    '''

    responses = {}  # where responses are registered
    requests = []  # where request history is storaged

    @classmethod
    def register_response(cls, path, method='GET', headers={},
                          body=None, status_code=200):
        '''
        This method is responsible for registering a response for a given
        request.
        '''
        cls.responses[path] = cls.responses.get(path, {})
        cls.responses[path][method] = Response(status_code, headers, body)

    @classmethod
    def reset(cls):
        '''
        Removes all registered responses and cleans request history
        '''
        cls.requests = []
        cls.responses = {}

    def generic_handler(f):
        @wraps(f)
        def wrapped(self):
            # Adds request into the request history
            self.requests.append(Request(self))

            # Check if path exists. If not, throw a 404.
            path = self.responses.get(self.path, None)
            if path is None:
                self.send_error(
                    404,
                    '{} is not a registered path'.format(self.path)
                )
                return None

            # Check if method is allowed. If not, throw a 405.
            response = path.get(self.command, None)
            if response is None:
                self.send_error(
                    405,
                    '{} method is not allowed'.format(self.command)
                )
                return None

            # Start to send the response
            self.send_response(response.status_code)
            for header in response.headers.items():
                self.send_header(*header)
            self.end_headers()
            if response.body:
                self.wfile.write(response.body.encode())
        return wrapped

    @generic_handler
    def do_POST(self):
        pass

    @generic_handler
    def do_GET(self):
        pass

    @generic_handler
    def do_PUT(self):
        pass

    @generic_handler
    def do_DELETE(self):
        pass

    @generic_handler
    def do_HEAD(self):
        pass


class HTTPMockServer(HTTPServer):

    def __init__(self):
        super().__init__(('0.0.0.0', 0), RequestHandler)

    def start(self):
        threading.Thread(target=self.serve_forever).start()
