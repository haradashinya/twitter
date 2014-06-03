from unittest import skipUnless

from django.core.management.color import no_style
from django.db import connection
from django.test import TestCase

from .models import Article, IndexTogetherSingleList


class IndexesTests(TestCase):
    def test_index_together(self):
        index_sql = connection.creation.sql_indexes_for_model(Article, no_style())
        self.assertEqual(len(index_sql), 1)

    def test_index_together_single_list(self):
        # Test for using index_together with a single list (#22172)
        index_sql = connection.creation.sql_indexes_for_model(IndexTogetherSingleList, no_style())
        self.assertEqual(len(index_sql), 1)

    @skipUnless(connection.vendor == 'postgresql',
        "This is a postgresql-specific issue")
    def test_postgresql_text_indexes(self):
        """Test creation of PostgreSQL-specific text indexes (#12234)"""
        from .models import IndexedArticle
        index_sql = connection.creation.sql_indexes_for_model(IndexedArticle, no_style())
        self.assertEqual(len(index_sql), 5)
        self.assertIn('("headline" varchar_pattern_ops)', index_sql[1])
        self.assertIn('("body" text_pattern_ops)', index_sql[3])
        # unique=True and db_index=True should only create the varchar-specific
        # index (#19441).
        self.assertIn('("slug" varchar_pattern_ops)', index_sql[4])
