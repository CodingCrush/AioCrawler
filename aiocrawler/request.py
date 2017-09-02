from user_agent import generate_user_agent, generate_navigator, \
    generate_navigator_js


# Factory Mode
def random_navigator_headers(*args):
    # "user_agent"-> "User-Agent
    raw_headers = generate_navigator()
    return {
        header.title().replace("_", "-"): value
        for header, value in raw_headers.items() if value is not None
    }


def random_navigator_js_headers(*args):
    raw_headers = generate_navigator_js()
    return {
        header: value
        for header, value in raw_headers.items() if value is not None
    }


def random_user_agent(*args):
    return {
        'User-Agent': generate_user_agent()
    }
