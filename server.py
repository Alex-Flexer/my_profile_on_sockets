import socket
from threading import Thread
from typing import Callable
import re
from http import HTTPStatus
from json import dumps
from os import walk
from os.path import join
from mimetypes import guess_type


RAW_RESPONSE_PATTER =\
    b"""HTTP/1.1 %b %b\r
Content-Type: %b\r
Connection: close\r
%b

%b"""


class Server:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.handlers = {}

    def bind_handlers(self, handlers: dict[tuple[str, str], Callable]):
        self.handlers.update(handlers)

    def _parse_body(self, data: str) -> dict:
        body_match = re.search(r"\r?\n\r?\n(.*)$", data, re.DOTALL)
        res = {}
        if body_match:
            body = body_match.group(1)
            params = body.split("&")
            for param in params:
                if "=" in param:
                    key, value = param.split("=", 1)
                    res[key] = value

        return res

    def _parse_headers(self, data: str) -> dict:
        headers = {}
        lines = data.strip().split('\n')

        for line in lines[1:]:
            if ':' in line:
                key, value = line.split(':', 1)
                headers[key.strip()] = value.strip()
            else:
                break

        return headers

    def _request_handler(self, conn, addr):
        with conn:
            data: str = conn.recv(1024).decode('utf-8')

            match = re.match(r"^(GET|POST|PUT|DELETE|HEAD|OPTIONS|PATCH)\s+([^?\s]+)", data)

            if match:
                http_method = match.group(1)
                path = match.group(2)

                headers = self._parse_headers(data)
                body = self._parse_body(data)
            else:
                print(data)
                raise ValueError("Invalid HTTP request")

            handler: Callable = self.handlers.get(
                (http_method, path), lambda: FileResponse("./static/forbidden/page.html", status=404)
            )

            args_cnt = handler.__code__.co_argcount

            if args_cnt > 1:
                raise ValueError(f"Handler must get 0 or 1 argument, not {args_cnt}")

            response: Response = handler(Request(headers, body)) if args_cnt == 1 else handler()
            conn.sendall(response.response)

    def mount(self, dir_path: str,) -> None:
        files_paths = []
        for path, _, files in walk(dir_path):
            files_paths += [join(path, file) for file in files]

        lambda_maker = lambda x: lambda: x

        self.bind_handlers({
            ("GET", file_path.lstrip('.')): lambda_maker(FileResponse(file_path))
            for file_path in files_paths
        })

    def run(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind((self.host, self.port))
            s.listen()
            while True:
                conn, addr = s.accept()
                thr = Thread(target=self._request_handler, args=(conn, addr))
                thr.start()


class Request:
    body: dict
    headers: dict

    def __init__(self, headers: dict, body: dict = {}):
        self.headers = headers
        self.body = body


class Response:
    response: str

    def _dict2headers(self, headers: dict) -> str:
        return "\n".join([f"{key}: {value}" for key, value in headers.items()])

    def __init__(self, resp_type: str, status: int, headers: str = "", data: bytes = b"") -> None:
        self.response = RAW_RESPONSE_PATTER % (
            str(status).encode("utf-8"),
            HTTPStatus(status).description.encode("utf-8"),
            resp_type.encode("utf-8"),
            headers.encode("utf-8"),
            data
        )


class TextResponse(Response):
    def __init__(self, data: str = "", headers: dict = {}, status: int = 200) -> None:
        headers = super()._dict2headers(headers)
        super().__init__("text/html", status, headers, data)


class JsonResponse(Response):
    def __init__(self, data: dict = {}, headers: dict = {}, status: int = 200) -> None:
        headers = super()._dict2headers(headers)
        json = dumps(data, ensure_ascii=False)
        super().__init__("application/x-www-form-urlencoded", status, headers, json)


class FileResponse(Response):
    def __init__(self, file_path: str, headers: dict = {}, status: int = 200) -> None:
        with open(file_path, 'rb') as file:
            data = file.read()

        headers["Content-Length"] = str(len(data))
        headers = super()._dict2headers(headers)

        super().__init__(guess_type(file_path)[0], status, headers, data)
