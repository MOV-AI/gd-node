class HttpMessage:
    """Messsage"""

    def __init__(self, app=None, req=None):

        self.req = req
        self.app = app
