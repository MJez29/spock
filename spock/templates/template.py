from importlib import resources as pkg_resources
from spock import templates

authorizedHtml = None
errorHtml = None


def get_error_page(error_code):
    global errorHtml
    if not errorHtml:
        errorHtml = pkg_resources.open_text(templates, "error.html").read()
    return errorHtml.replace("<error_code>", error_code).encode()


def get_authorized_page():
    global authorizedHtml
    if not authorizedHtml:
        authorizedHtml = pkg_resources.open_text(templates, "authorized.html").read()
    return authorizedHtml.encode()
