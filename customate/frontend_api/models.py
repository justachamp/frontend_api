from django.db import models
from django.conf import settings
from django.contrib.auth import get_user_model
from pygments.lexers import get_all_lexers
from pygments.styles import get_all_styles
from rest_framework.utils import formatting

from pygments.lexers import get_lexer_by_name
from pygments.formatters.html import HtmlFormatter
from pygments import highlight
from core.models import Model, User

# LEXERS = [item for item in get_all_lexers() if item[1]]
# LANGUAGE_CHOICES = sorted([(item[1][0], item[0]) for item in LEXERS])
# STYLE_CHOICES = sorted((item, item) for item in get_all_styles())

# Create your models here.


class Address(Model):
    user = models.ForeignKey(User, related_name='address', on_delete=models.CASCADE)
    address = models.CharField(max_length=250)
    country = models.CharField(max_length=50)
    address_line_1 = models.CharField(max_length=100)
    address_line_2 = models.CharField(max_length=100)
    city = models.CharField(max_length=50)
    locality = models.CharField(max_length=50)
    postcode = models.CharField(max_length=20)

    def __str__(self):
        return "%s the address" % self.address


class Account(Model):
    user = models.ForeignKey(User, related_name='account', on_delete=models.CASCADE)
    COLOR_CHOICES = (
        ('Personal', 'personal'),
        ('Business', 'business')
    )

    account_type = models.CharField(max_length=10, choices=COLOR_CHOICES, default='Personal')

    def __str__(self):
        return "%s the account" % self.type

# class Snippet(Model):
#     created = models.DateTimeField(auto_now_add=True)
#     title = models.CharField(max_length=100, blank=True, default='')
#     code = models.TextField()
#     linenos = models.BooleanField(default=False)
#     language = models.CharField(choices=LANGUAGE_CHOICES, default='python', max_length=100)
#     style = models.CharField(choices=STYLE_CHOICES, default='friendly', max_length=100)
#     owner = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='snippets', on_delete=models.CASCADE)
#     highlighted = models.TextField()
#
#     def save(self, *args, **kwargs):
#         """
#         Use the `pygments` library to create a highlighted HTML
#         representation of the code snippet.
#         """
#         lexer = get_lexer_by_name(self.language)
#         linenos = 'table' if self.linenos else False
#         options = {'title': self.title} if self.title else {}
#         formatter = HtmlFormatter(style=self.style, linenos=linenos,
#                                   full=True, **options)
#         self.highlighted = highlight(self.code, lexer, formatter)
#         super(Snippet, self).save(*args, **kwargs)
#
#     class Meta:
#         ordering = ('created',)
