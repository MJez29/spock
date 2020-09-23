authorizedHtml = None
errorHtml = None


def get_error_page(error_code):
    global errorHtml
    if not errorHtml:
        errorHtml = open("spock/templates/error.html").read()
    return errorHtml.replace("<error_code>", error_code).encode()


def get_authorized_page():
    global authorizedHtml
    if not authorizedHtml:
        authorizedHtml = open("spock/templates/authorized.html").read()
    return authorizedHtml.encode()
