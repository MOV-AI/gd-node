# @TODO: pass HttpMessage to the callback
# @TODO: define message structure
class HttpMessage:
    """Messsage"""

    def __init__(self, app=None, req=None):

        self.req = req
        self.app = app
