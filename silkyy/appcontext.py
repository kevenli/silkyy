import functools

class InvalidApplicatoinContextRequestException(Exception):
    def __init__(self, message="Invalid application context request."):
        super(InvalidApplicatoinContextRequestException, self).__init__(message)

class ApplicationContextProvider():
    def verify_request(self, request):
        return ""


class DatabaseApplicationContextProvider(ApplicationContextProvider):
    def verify_request(self, request):
        app_key = request.headers.get('X-Silkyy-AppKey')
        request_digest = request.headers.get('X-Silkyy-Digest')

        # TODO: implement app data persistence
        # app = models.App.find_by_app_key(app_key)
        # app_cache[app_key] = app
        # hash = new hash(app.secret_key)
        # hash.update(request.METHOD)
        # hash.update(request.URI)
        # hash.update(request.BODY)
        # digest = hash.digest()
        # if request_digest != digest:
        #    raise new InvalidApplicatoinContextRequestException
        #  return True, app.id

def api_request_validate(method):
    @functools.wraps(method)
    def wrapper(self, *args, **kwargs):
        context_provider = self.settings.get('app_context_provider')
        if context_provider is None:
            raise Exception('No app_context_provider assgiend. Set it into application settings.')

        request = self.request
        app_id = context_provider.verify_request(request)
        self.app_id = app_id
        return method(self, *args, **kwargs)

    return wrapper
