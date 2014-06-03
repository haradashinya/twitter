import os
import sys
from types import ModuleType
import unittest
import warnings

from django.conf import LazySettings, Settings, settings
from django.core.exceptions import ImproperlyConfigured
from django.http import HttpRequest
from django.test import (SimpleTestCase, TransactionTestCase, TestCase,
    modify_settings, override_settings, signals)
from django.utils import six


@modify_settings(ITEMS={
    'prepend': ['b'],
    'append': ['d'],
    'remove': ['a', 'e']
})
@override_settings(ITEMS=['a', 'c', 'e'], ITEMS_OUTER=[1, 2, 3],
                   TEST='override', TEST_OUTER='outer')
class FullyDecoratedTranTestCase(TransactionTestCase):

    available_apps = []

    def test_override(self):
        self.assertListEqual(settings.ITEMS, ['b', 'c', 'd'])
        self.assertListEqual(settings.ITEMS_OUTER, [1, 2, 3])
        self.assertEqual(settings.TEST, 'override')
        self.assertEqual(settings.TEST_OUTER, 'outer')

    @modify_settings(ITEMS={
        'append': ['e', 'f'],
        'prepend': ['a'],
        'remove': ['d', 'c'],
    })
    def test_method_list_override(self):
        self.assertListEqual(settings.ITEMS, ['a', 'b', 'e', 'f'])
        self.assertListEqual(settings.ITEMS_OUTER, [1, 2, 3])

    @modify_settings(ITEMS={
        'append': ['b'],
        'prepend': ['d'],
        'remove': ['a', 'c', 'e'],
    })
    def test_method_list_override_no_ops(self):
        self.assertListEqual(settings.ITEMS, ['b', 'd'])

    @modify_settings(ITEMS={
        'append': 'e',
        'prepend': 'a',
        'remove': 'c',
    })
    def test_method_list_override_strings(self):
        self.assertListEqual(settings.ITEMS, ['a', 'b', 'd', 'e'])

    @modify_settings(ITEMS={'remove': ['b', 'd']})
    @modify_settings(ITEMS={'append': ['b'], 'prepend': ['d']})
    def test_method_list_override_nested_order(self):
        self.assertListEqual(settings.ITEMS, ['d', 'c', 'b'])

    @override_settings(TEST='override2')
    def test_method_override(self):
        self.assertEqual(settings.TEST, 'override2')
        self.assertEqual(settings.TEST_OUTER, 'outer')

    def test_decorated_testcase_name(self):
        self.assertEqual(FullyDecoratedTranTestCase.__name__, 'FullyDecoratedTranTestCase')

    def test_decorated_testcase_module(self):
        self.assertEqual(FullyDecoratedTranTestCase.__module__, __name__)


@modify_settings(ITEMS={
    'prepend': ['b'],
    'append': ['d'],
    'remove': ['a', 'e']
})
@override_settings(ITEMS=['a', 'c', 'e'], TEST='override')
class FullyDecoratedTestCase(TestCase):

    def test_override(self):
        self.assertListEqual(settings.ITEMS, ['b', 'c', 'd'])
        self.assertEqual(settings.TEST, 'override')

    @modify_settings(ITEMS={
        'append': 'e',
        'prepend': 'a',
        'remove': 'c',
    })
    @override_settings(TEST='override2')
    def test_method_override(self):
        self.assertListEqual(settings.ITEMS, ['a', 'b', 'd', 'e'])
        self.assertEqual(settings.TEST, 'override2')


class ClassDecoratedTestCaseSuper(TestCase):
    """
    Dummy class for testing max recursion error in child class call to
    super().  Refs #17011.

    """
    def test_max_recursion_error(self):
        pass


@override_settings(TEST='override')
class ClassDecoratedTestCase(ClassDecoratedTestCaseSuper):
    def test_override(self):
        self.assertEqual(settings.TEST, 'override')

    @override_settings(TEST='override2')
    def test_method_override(self):
        self.assertEqual(settings.TEST, 'override2')

    def test_max_recursion_error(self):
        """
        Overriding a method on a super class and then calling that method on
        the super class should not trigger infinite recursion. See #17011.

        """
        try:
            super(ClassDecoratedTestCase, self).test_max_recursion_error()
        except RuntimeError:
            self.fail()


@modify_settings(ITEMS={'append': 'mother'})
@override_settings(ITEMS=['father'], TEST='override-parent')
class ParentDecoratedTestCase(TestCase):
    pass


@modify_settings(ITEMS={'append': ['child']})
@override_settings(TEST='override-child')
class ChildDecoratedTestCase(ParentDecoratedTestCase):
    def test_override_settings_inheritance(self):
        self.assertEqual(settings.ITEMS, ['father', 'mother', 'child'])
        self.assertEqual(settings.TEST, 'override-child')


class SettingsTests(TestCase):
    def setUp(self):
        self.testvalue = None
        signals.setting_changed.connect(self.signal_callback)

    def tearDown(self):
        signals.setting_changed.disconnect(self.signal_callback)

    def signal_callback(self, sender, setting, value, **kwargs):
        if setting == 'TEST':
            self.testvalue = value

    def test_override(self):
        settings.TEST = 'test'
        self.assertEqual('test', settings.TEST)
        with self.settings(TEST='override'):
            self.assertEqual('override', settings.TEST)
        self.assertEqual('test', settings.TEST)
        del settings.TEST

    def test_override_change(self):
        settings.TEST = 'test'
        self.assertEqual('test', settings.TEST)
        with self.settings(TEST='override'):
            self.assertEqual('override', settings.TEST)
            settings.TEST = 'test2'
        self.assertEqual('test', settings.TEST)
        del settings.TEST

    def test_override_doesnt_leak(self):
        self.assertRaises(AttributeError, getattr, settings, 'TEST')
        with self.settings(TEST='override'):
            self.assertEqual('override', settings.TEST)
            settings.TEST = 'test'
        self.assertRaises(AttributeError, getattr, settings, 'TEST')

    @override_settings(TEST='override')
    def test_decorator(self):
        self.assertEqual('override', settings.TEST)

    def test_context_manager(self):
        self.assertRaises(AttributeError, getattr, settings, 'TEST')
        override = override_settings(TEST='override')
        self.assertRaises(AttributeError, getattr, settings, 'TEST')
        override.enable()
        self.assertEqual('override', settings.TEST)
        override.disable()
        self.assertRaises(AttributeError, getattr, settings, 'TEST')

    def test_class_decorator(self):
        # SimpleTestCase can be decorated by override_settings, but not ut.TestCase
        class SimpleTestCaseSubclass(SimpleTestCase):
            pass

        class UnittestTestCaseSubclass(unittest.TestCase):
            pass

        decorated = override_settings(TEST='override')(SimpleTestCaseSubclass)
        self.assertIsInstance(decorated, type)
        self.assertTrue(issubclass(decorated, SimpleTestCase))

        with six.assertRaisesRegex(self, Exception,
                "Only subclasses of Django SimpleTestCase*"):
            decorated = override_settings(TEST='override')(UnittestTestCaseSubclass)

    def test_signal_callback_context_manager(self):
        self.assertRaises(AttributeError, getattr, settings, 'TEST')
        with self.settings(TEST='override'):
            self.assertEqual(self.testvalue, 'override')
        self.assertEqual(self.testvalue, None)

    @override_settings(TEST='override')
    def test_signal_callback_decorator(self):
        self.assertEqual(self.testvalue, 'override')

    #
    # Regression tests for #10130: deleting settings.
    #

    def test_settings_delete(self):
        settings.TEST = 'test'
        self.assertEqual('test', settings.TEST)
        del settings.TEST
        self.assertRaises(AttributeError, getattr, settings, 'TEST')

    def test_settings_delete_wrapped(self):
        self.assertRaises(TypeError, delattr, settings, '_wrapped')

    def test_override_settings_delete(self):
        """
        Allow deletion of a setting in an overridden settings set (#18824)
        """
        previous_i18n = settings.USE_I18N
        previous_l10n = settings.USE_L10N
        with self.settings(USE_I18N=False):
            del settings.USE_I18N
            self.assertRaises(AttributeError, getattr, settings, 'USE_I18N')
            # Should also work for a non-overridden setting
            del settings.USE_L10N
            self.assertRaises(AttributeError, getattr, settings, 'USE_L10N')
        self.assertEqual(settings.USE_I18N, previous_i18n)
        self.assertEqual(settings.USE_L10N, previous_l10n)

    def test_override_settings_nested(self):
        """
        Test that override_settings uses the actual _wrapped attribute at
        runtime, not when it was instantiated.
        """

        self.assertRaises(AttributeError, getattr, settings, 'TEST')
        self.assertRaises(AttributeError, getattr, settings, 'TEST2')

        inner = override_settings(TEST2='override')
        with override_settings(TEST='override'):
            self.assertEqual('override', settings.TEST)
            with inner:
                self.assertEqual('override', settings.TEST)
                self.assertEqual('override', settings.TEST2)
            # inner's __exit__ should have restored the settings of the outer
            # context manager, not those when the class was instantiated
            self.assertEqual('override', settings.TEST)
            self.assertRaises(AttributeError, getattr, settings, 'TEST2')

        self.assertRaises(AttributeError, getattr, settings, 'TEST')
        self.assertRaises(AttributeError, getattr, settings, 'TEST2')

    def test_allowed_include_roots_string(self):
        """
        ALLOWED_INCLUDE_ROOTS is not allowed to be incorrectly set to a string
        rather than a tuple.
        """
        self.assertRaises(ValueError, setattr, settings,
            'ALLOWED_INCLUDE_ROOTS', '/var/www/ssi/')


class TestComplexSettingOverride(TestCase):
    def setUp(self):
        self.old_warn_override_settings = signals.COMPLEX_OVERRIDE_SETTINGS.copy()
        signals.COMPLEX_OVERRIDE_SETTINGS.add('TEST_WARN')

    def tearDown(self):
        signals.COMPLEX_OVERRIDE_SETTINGS = self.old_warn_override_settings
        self.assertFalse('TEST_WARN' in signals.COMPLEX_OVERRIDE_SETTINGS)

    def test_complex_override_warning(self):
        """Regression test for #19031"""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")

            with override_settings(TEST_WARN='override'):
                self.assertEqual(settings.TEST_WARN, 'override')

            self.assertEqual(len(w), 1)
            # File extension may by .py, .pyc, etc. Compare only basename.
            self.assertEqual(os.path.splitext(w[0].filename)[0],
                             os.path.splitext(__file__)[0])
            self.assertEqual(str(w[0].message),
                'Overriding setting TEST_WARN can lead to unexpected behavior.')


class TrailingSlashURLTests(TestCase):
    """
    Tests for the MEDIA_URL and STATIC_URL settings.

    They must end with a slash to ensure there's a deterministic way to build
    paths in templates.
    """
    settings_module = settings

    def setUp(self):
        self._original_media_url = self.settings_module.MEDIA_URL
        self._original_static_url = self.settings_module.STATIC_URL

    def tearDown(self):
        self.settings_module.MEDIA_URL = self._original_media_url
        self.settings_module.STATIC_URL = self._original_static_url

    def test_blank(self):
        """
        The empty string is accepted, even though it doesn't end in a slash.
        """
        self.settings_module.MEDIA_URL = ''
        self.assertEqual('', self.settings_module.MEDIA_URL)

        self.settings_module.STATIC_URL = ''
        self.assertEqual('', self.settings_module.STATIC_URL)

    def test_end_slash(self):
        """
        It works if the value ends in a slash.
        """
        self.settings_module.MEDIA_URL = '/foo/'
        self.assertEqual('/foo/', self.settings_module.MEDIA_URL)

        self.settings_module.MEDIA_URL = 'http://media.foo.com/'
        self.assertEqual('http://media.foo.com/',
                         self.settings_module.MEDIA_URL)

        self.settings_module.STATIC_URL = '/foo/'
        self.assertEqual('/foo/', self.settings_module.STATIC_URL)

        self.settings_module.STATIC_URL = 'http://static.foo.com/'
        self.assertEqual('http://static.foo.com/',
                         self.settings_module.STATIC_URL)

    def test_no_end_slash(self):
        """
        An ImproperlyConfigured exception is raised if the value doesn't end
        in a slash.
        """
        with self.assertRaises(ImproperlyConfigured):
            self.settings_module.MEDIA_URL = '/foo'

        with self.assertRaises(ImproperlyConfigured):
            self.settings_module.MEDIA_URL = 'http://media.foo.com'

        with self.assertRaises(ImproperlyConfigured):
            self.settings_module.STATIC_URL = '/foo'

        with self.assertRaises(ImproperlyConfigured):
            self.settings_module.STATIC_URL = 'http://static.foo.com'

    def test_double_slash(self):
        """
        If the value ends in more than one slash, presume they know what
        they're doing.
        """
        self.settings_module.MEDIA_URL = '/stupid//'
        self.assertEqual('/stupid//', self.settings_module.MEDIA_URL)

        self.settings_module.MEDIA_URL = 'http://media.foo.com/stupid//'
        self.assertEqual('http://media.foo.com/stupid//',
                         self.settings_module.MEDIA_URL)

        self.settings_module.STATIC_URL = '/stupid//'
        self.assertEqual('/stupid//', self.settings_module.STATIC_URL)

        self.settings_module.STATIC_URL = 'http://static.foo.com/stupid//'
        self.assertEqual('http://static.foo.com/stupid//',
                         self.settings_module.STATIC_URL)


class SecureProxySslHeaderTest(TestCase):
    settings_module = settings

    def setUp(self):
        self._original_setting = self.settings_module.SECURE_PROXY_SSL_HEADER

    def tearDown(self):
        self.settings_module.SECURE_PROXY_SSL_HEADER = self._original_setting

    def test_none(self):
        self.settings_module.SECURE_PROXY_SSL_HEADER = None
        req = HttpRequest()
        self.assertEqual(req.is_secure(), False)

    def test_set_without_xheader(self):
        self.settings_module.SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTOCOL', 'https')
        req = HttpRequest()
        self.assertEqual(req.is_secure(), False)

    def test_set_with_xheader_wrong(self):
        self.settings_module.SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTOCOL', 'https')
        req = HttpRequest()
        req.META['HTTP_X_FORWARDED_PROTOCOL'] = 'wrongvalue'
        self.assertEqual(req.is_secure(), False)

    def test_set_with_xheader_right(self):
        self.settings_module.SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTOCOL', 'https')
        req = HttpRequest()
        req.META['HTTP_X_FORWARDED_PROTOCOL'] = 'https'
        self.assertEqual(req.is_secure(), True)


class IsOverriddenTest(TestCase):
    def test_configure(self):
        s = LazySettings()
        s.configure(SECRET_KEY='foo')

        self.assertTrue(s.is_overridden('SECRET_KEY'))

    def test_module(self):
        settings_module = ModuleType('fake_settings_module')
        settings_module.SECRET_KEY = 'foo'
        sys.modules['fake_settings_module'] = settings_module
        try:
            s = Settings('fake_settings_module')

            self.assertTrue(s.is_overridden('SECRET_KEY'))
            self.assertFalse(s.is_overridden('TEMPLATE_LOADERS'))
        finally:
            del sys.modules['fake_settings_module']

    def test_override(self):
        self.assertFalse(settings.is_overridden('TEMPLATE_LOADERS'))
        with override_settings(TEMPLATE_LOADERS=[]):
            self.assertTrue(settings.is_overridden('TEMPLATE_LOADERS'))
