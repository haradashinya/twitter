from django.apps import AppConfig
from django.apps.registry import Apps
from django.db import models
from django.db.models.options import DEFAULT_NAMES, normalize_together
from django.utils import six
from django.utils.module_loading import import_string


class InvalidBasesError(ValueError):
    pass


class ProjectState(object):
    """
    Represents the entire project's overall state.
    This is the item that is passed around - we do it here rather than at the
    app level so that cross-app FKs/etc. resolve properly.
    """

    def __init__(self, models=None):
        self.models = models or {}
        self.apps = None

    def add_model_state(self, model_state):
        self.models[(model_state.app_label, model_state.name.lower())] = model_state

    def clone(self):
        "Returns an exact copy of this ProjectState"
        return ProjectState(
            models=dict((k, v.clone()) for k, v in self.models.items())
        )

    def render(self):
        "Turns the project state into actual models in a new Apps"
        if self.apps is None:
            # Populate the app registry with a stub for each application.
            app_labels = set(model_state.app_label for model_state in self.models.values())
            self.apps = Apps([AppConfigStub(label) for label in sorted(app_labels)])
            # We keep trying to render the models in a loop, ignoring invalid
            # base errors, until the size of the unrendered models doesn't
            # decrease by at least one, meaning there's a base dependency loop/
            # missing base.
            unrendered_models = list(self.models.values())
            while unrendered_models:
                new_unrendered_models = []
                for model in unrendered_models:
                    try:
                        model.render(self.apps)
                    except InvalidBasesError:
                        new_unrendered_models.append(model)
                if len(new_unrendered_models) == len(unrendered_models):
                    raise InvalidBasesError("Cannot resolve bases for %r" % new_unrendered_models)
                unrendered_models = new_unrendered_models
        return self.apps

    @classmethod
    def from_apps(cls, apps):
        "Takes in an Apps and returns a ProjectState matching it"
        app_models = {}
        for model in apps.get_models():
            model_state = ModelState.from_model(model)
            app_models[(model_state.app_label, model_state.name.lower())] = model_state
        return cls(app_models)

    def __eq__(self, other):
        if set(self.models.keys()) != set(other.models.keys()):
            return False
        return all(model == other.models[key] for key, model in self.models.items())

    def __ne__(self, other):
        return not (self == other)


class AppConfigStub(AppConfig):
    """
    Stubs a Django AppConfig. Only provides a label, and a dict of models.
    """
    # Not used, but required by AppConfig.__init__
    path = ''

    def __init__(self, label):
        super(AppConfigStub, self).__init__(label, None)

    def import_models(self, all_models):
        self.models = all_models


class ModelState(object):
    """
    Represents a Django Model. We don't use the actual Model class
    as it's not designed to have its options changed - instead, we
    mutate this one and then render it into a Model as required.

    Note that while you are allowed to mutate .fields, you are not allowed
    to mutate the Field instances inside there themselves - you must instead
    assign new ones, as these are not detached during a clone.
    """

    def __init__(self, app_label, name, fields, options=None, bases=None):
        self.app_label = app_label
        self.name = name
        self.fields = fields
        self.options = options or {}
        self.bases = bases or (models.Model, )
        # Sanity-check that fields is NOT a dict. It must be ordered.
        if isinstance(self.fields, dict):
            raise ValueError("ModelState.fields cannot be a dict - it must be a list of 2-tuples.")

    @classmethod
    def from_model(cls, model):
        """
        Feed me a model, get a ModelState representing it out.
        """
        # Deconstruct the fields
        fields = []
        for field in model._meta.local_fields:
            name, path, args, kwargs = field.deconstruct()
            field_class = import_string(path)
            try:
                fields.append((name, field_class(*args, **kwargs)))
            except TypeError as e:
                raise TypeError("Couldn't reconstruct field %s on %s.%s: %s" % (
                    name,
                    model._meta.app_label,
                    model._meta.object_name,
                    e,
                ))
        for field in model._meta.local_many_to_many:
            name, path, args, kwargs = field.deconstruct()
            field_class = import_string(path)
            try:
                fields.append((name, field_class(*args, **kwargs)))
            except TypeError as e:
                raise TypeError("Couldn't reconstruct m2m field %s on %s: %s" % (
                    name,
                    model._meta.object_name,
                    e,
                ))
        # Extract the options
        options = {}
        for name in DEFAULT_NAMES:
            # Ignore some special options
            if name in ["apps", "app_label"]:
                continue
            elif name in model._meta.original_attrs:
                if name == "unique_together":
                    ut = model._meta.original_attrs["unique_together"]
                    options[name] = set(normalize_together(ut))
                elif name == "index_together":
                    it = model._meta.original_attrs["index_together"]
                    options[name] = set(normalize_together(it))
                else:
                    options[name] = model._meta.original_attrs[name]

        def flatten_bases(model):
            bases = []
            for base in model.__bases__:
                if hasattr(base, "_meta") and base._meta.abstract:
                    bases.extend(flatten_bases(base))
                else:
                    bases.append(base)
            return bases

        # We can't rely on __mro__ directly because we only want to flatten
        # abstract models and not the whole tree. However by recursing on
        # __bases__ we may end up with duplicates and ordering issues, we
        # therefore discard any duplicates and reorder the bases according
        # to their index in the MRO.
        flattened_bases = sorted(set(flatten_bases(model)), key=lambda x: model.__mro__.index(x))

        # Make our record
        bases = tuple(
            (
                "%s.%s" % (base._meta.app_label, base._meta.model_name)
                if hasattr(base, "_meta") else
                base
            )
            for base in flattened_bases
        )
        # Ensure at least one base inherits from models.Model
        if not any((isinstance(base, six.string_types) or issubclass(base, models.Model)) for base in bases):
            bases = (models.Model,)
        return cls(
            model._meta.app_label,
            model._meta.object_name,
            fields,
            options,
            bases,
        )

    def clone(self):
        "Returns an exact copy of this ModelState"
        # We deep-clone the fields using deconstruction
        fields = []
        for name, field in self.fields:
            _, path, args, kwargs = field.deconstruct()
            field_class = import_string(path)
            fields.append((name, field_class(*args, **kwargs)))
        # Now make a copy
        return self.__class__(
            app_label=self.app_label,
            name=self.name,
            fields=fields,
            options=dict(self.options),
            bases=self.bases,
        )

    def render(self, apps):
        "Creates a Model object from our current state into the given apps"
        # First, make a Meta object
        meta_contents = {'app_label': self.app_label, "apps": apps}
        meta_contents.update(self.options)
        if "unique_together" in meta_contents:
            meta_contents["unique_together"] = list(meta_contents["unique_together"])
        meta = type("Meta", tuple(), meta_contents)
        # Then, work out our bases
        try:
            bases = tuple(
                (apps.get_model(base) if isinstance(base, six.string_types) else base)
                for base in self.bases
            )
        except LookupError:
            raise InvalidBasesError("Cannot resolve one or more bases from %r" % (self.bases,))
        # Turn fields into a dict for the body, add other bits
        body = dict(self.fields)
        body['Meta'] = meta
        body['__module__'] = "__fake__"
        # Then, make a Model object
        return type(
            self.name,
            bases,
            body,
        )

    def get_field_by_name(self, name):
        for fname, field in self.fields:
            if fname == name:
                return field
        raise ValueError("No field called %s on model %s" % (name, self.name))

    def __eq__(self, other):
        return (
            (self.app_label == other.app_label) and
            (self.name == other.name) and
            (len(self.fields) == len(other.fields)) and
            all((k1 == k2 and (f1.deconstruct()[1:] == f2.deconstruct()[1:])) for (k1, f1), (k2, f2) in zip(self.fields, other.fields)) and
            (self.options == other.options) and
            (self.bases == other.bases)
        )

    def __ne__(self, other):
        return not (self == other)
