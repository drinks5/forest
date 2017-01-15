from .exceptions import InvalidUsage
from collections import namedtuple
Route = namedtuple('Route', ['base', 'path'])


class Router:
    def __init__(self):
        self.registry = []

    def register(self, prefix, viewset, base_name=None):
        base_name = base_name and self.get_default_base_name(viewset)
        self.registry.append((prefix, viewset, base_name))
        # class ResourceViewSet:
        #     route = dict(base=None, path='resource')


class ViewsSet:
    decorators = []
    route = None

    def dispatch(self, request, *args, **kwargs):
        handler = getattr(self, request.method.lower(), None)
        if handler:
            return handler(request, *args, **kwargs)
        raise InvalidUsage(
            'Method {} not allowed for URL {}'.format(
                request.method, request.url), status_code=405)

    @classmethod
    def as_view(cls, *class_args, **class_kwargs):
        """ Converts the class into an actual view function that can be used
        with the routing system.

        """
        def view(*args, **kwargs):
            self = view.view_class(*class_args, **class_kwargs)
            return self.dispatch(*args, **kwargs)

        if cls.decorators:
            view.__module__ = cls.__module__
            for decorator in cls.decorators:
                view = decorator(view)

        view.view_class = cls
        view.__doc__ = cls.__doc__
        view.__module__ = cls.__module__
        return view
