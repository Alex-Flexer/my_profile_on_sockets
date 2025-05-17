from server import Server, FileResponse


server = Server("localhost", 8082)


def handler_home_page() -> FileResponse:
    return FileResponse("static/index/page.html", status=200)


def handler_about_page() -> FileResponse:
    return FileResponse("static/about/page.html", status=200)


def handler_contact_page() -> FileResponse:
    return FileResponse("static/contact/page.html", status=200)


def handler_projects_page() -> FileResponse:
    return FileResponse("static/projects/page.html", status=200)


def handler_icon() -> FileResponse:
    return FileResponse("static/favicon.ico", status=200)


if __name__ == "__main__":
    server.bind_handlers({
        ("GET", "/"): handler_home_page,
        ("GET", "/about"): handler_about_page,
        ("GET", "/contact"): handler_contact_page,
        ("GET", "/favicon.ico"): handler_icon,
        ("GET", "/projects"): handler_projects_page
    })

    server.mount("./static")
    server.run()
