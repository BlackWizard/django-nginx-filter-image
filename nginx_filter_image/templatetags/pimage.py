# -*- coding: utf-8 -*-

import re
import hashlib
from urllib import unquote
from random import choice

from django import template
from django.conf import settings
from django.template.defaultfilters import stringfilter
from django.utils.encoding import smart_unicode, iri_to_uri
from django.utils.safestring import mark_safe

register = template.Library()

pimage_stripschema_re = re.compile(r'^https?://|^//')
pimage_fixdupslash_re = re.compile(r'//*')
pimage_fixdotslash_re = re.compile(r'/\./')
pimage_fixamp_re = re.compile(r'&amp;')
pimage_url = getattr(settings, 'PROXY_IMAGE_URL', settings.STATIC_URL)
pimage_secret = getattr(settings, 'PROXY_IMAGE_SECRET', '')
pimage_proxy_param = getattr(settings, 'PROXY_IMAGE_PARAM', 'o')

import logging
log = logging.getLogger(__name__)

@register.filter
@stringfilter
def pimage(url, proxy_param=pimage_proxy_param, proxy_url=pimage_url):
    """Generate image proxy url by given original image url
    Usage:
        src="{{ article.image.src|pimage:"80x60" }}"
    """
    if getattr(proxy_url, '__iter__', False): # iterable, mb list or tuple
        proxy_url = choice(proxy_url)

    url = smart_unicode(url)
    url = unquote(url)
    url = iri_to_uri(url)
    url = pimage_stripschema_re.sub('', url)
    url = pimage_fixdupslash_re.sub('/', url)
    url = pimage_fixdotslash_re.sub('/', url)
    url = pimage_fixamp_re.sub('&', url)
    url = quote(url, r'~*&$;:?/!,=()[]{}|+')

    return u'%s/%s/%s/%s' % (
        proxy_url,
        hashlib.md5('%s/%s%s' % (proxy_param, url, pimage_secret)).hexdigest(),
        proxy_param, url)

@register.filter
@stringfilter
def pimage_single(url, proxy_param=pimage_proxy_param):
    """Same as pimage but use only first host"""
    if getattr(pimage_url, '__iter__', False):
        return pimage(url, proxy_param, pimage_url[0])
    return pimage(url, proxy_param, pimage_url)

always_safe = \
        ('ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_.-')
_safemaps = {}


def quote(s, safe = '/'):
    """Replace special characters in string using the %xx escape.
    Dirty copypaste from urllib.py because we need hex in lowercase
    for unqoting/quoting stage in nginx's proxy module.
    """
    cachekey = (safe, always_safe)
    try:
        safe_map = _safemaps[cachekey]
    except KeyError:
        safe += always_safe
        safe_map = {}
        for i in range(256):
            c = chr(i)
            safe_map[c] = (c in safe) and c or ('%%%02x' % i)
        _safemaps[cachekey] = safe_map
    res = map(safe_map.__getitem__, s)
    return ''.join(res)


pimage_sizes_tpl = getattr(settings, 'PROXY_IMAGE_SIZES_TPL',
                          u' width="%d" height="%d"')
pimage_sizes_err_tpl = getattr(settings, 'PROXY_IMAGE_SIZES_ERR_TPL', u'')
pimage_sizes_width = getattr(settings, 'PROXY_IMAGE_SIZES_WIDTH', 'width')
pimage_sizes_height = getattr(settings, 'PROXY_IMAGE_SIZES_HEIGHT', 'height')


def pimage_sizes_render(x, y, is_rotated=False):
    return mark_safe(is_rotated and pimage_sizes_tpl % (y, x) or pimage_sizes_tpl % (x, y))

@register.filter
def pimage_sizes(image, proxy_param=pimage_proxy_param):
    """Return image actual dimensions
    Usage:
        ...{{ article.image|pimage_sizes:"80x60" }}"
    Output:
        ... width="200" height="100"
    """

    try:
        if image.field.width_field and image.field.height_field:
            sx = dx = getattr(image.instance, image.field.width_field)
            sy = dy = getattr(image.instance, image.field.height_field)
        else:
            raise AttributeError()
    except AttributeError:
        try:
            sx = dx = getattr(image, pimage_sizes_width)
            sy = dy = getattr(image, pimage_sizes_height)
            #log.debug("pimage: image size (%sx%s)" % (sx, sy))
        except AttributeError:
            return pimage_sizes_err_tpl

    if not (sx and sy):
        return pimage_sizes_err_tpl

    is_crop = False
    is_rotated = False
    if proxy_param.startswith('r'):
        if proxy_param.startswith('r90'):
            proxy_param = proxy_param.lstrip('r90x')
            is_rotated = True
        elif proxy_param.startswith('r270'):
            proxy_param = proxy_param.lstrip('r270x')
            is_rotated = True
        else:
            proxy_param = proxy_param.lstrip('r180x')
    elif proxy_param.startswith('c'):
        proxy_param = proxy_param.lstrip('c')
        is_crop = True
    elif proxy_param.startswith('o'):
        return pimage_sizes_render(dx, dy)

    try:
        max_width, max_height = proxy_param.split('x')
        if max_width == '-':
            max_height = int(max_height)
            if sy > max_height:
                return pimage_sizes_render(max_height * sx / sy, max_height, is_rotated)
            else: 
                return pimage_sizes_render(sx, sy, is_rotated)
        elif max_height == '-':
            max_width = int(max_width)
            if sx > max_width:
                return pimage_sizes_render(max_width, max_width * sy / sx, is_rotated)
            else:
                return pimage_sizes_render(sx, sy, is_rotated)
        else:
            max_width = int(max_width)
            max_height = int(max_height)
    except ValueError:
        return pimage_sizes_err_tpl

    if is_crop:
        if sx * 100 / sy < max_width * 100 / max_height:
            if sx > max_width:
                dy = sy * max_width / sx
                dx, dy = max_width, dy or 1
        elif sy > max_height:
            dx = sx * max_height / sy
            dx, dy = dx or 1, max_height
        if dx > max_width:
            dx = max_width
        if dy > max_height:
            dy = max_height
    else:
        if sx > max_width:
            dy = sy * max_width / sx
            dx, dy = max_width, dy or 1
        if dy > max_height:
            dx = sx * max_height / sy
            dx, dy = dx or 1, max_height

    return pimage_sizes_render(dx, dy, is_rotated)

pimage_tag_url = getattr(settings, 'PROXY_IMAGE_TAG_URL', 'url')
pimage_tag_err_tpl = getattr(settings, 'PROXY_IMAGE_TAG_ERR_TPL', u'')

class PImageNode(template.Node):
    def __init__(self, single, image, proxy_param=None, extra=None):
        self.image = template.Variable(image)
        self.proxy_param = proxy_param and template.Variable(proxy_param) or None
        self.extra = extra and template.Variable(extra) or None
        if single:
            self.pimage = pimage_single
        else:
            self.pimage = pimage

    def render(self, context):
        try:
            image = self.image.resolve(context)
            url = getattr(image, pimage_tag_url)
            if self.proxy_param is None:
                proxy_param = pimage_proxy_param
            else:
                proxy_param = self.proxy_param.resolve(context)
            if self.extra is None:
                extra = ''
            else:
                extra = self.extra.resolve(context)
        except:
            return pimage_tag_err_tpl

        return '<img src="%s"%s%s/>' % (self.pimage(url, proxy_param), pimage_sizes(image, proxy_param), extra and ' ' + extra or '')

@register.tag('pimage')
def pimage_tag(parser, token):
    """Return image tag
    Usage:
        ...{% pimage article.image "200x100" "style=\"border: 1px\"" %}
    Output:
        ...<img src="" width="200" height="100" style="border: 1px" />
    """
    contents = token.split_contents()

    return PImageNode(False, *contents[1:])
pimage_tag.is_safe = True


@register.tag('pimage_single')
def pimage_single_tag(parser, token):
    contents = token.split_contents()

    return PImageNode(True, *contents[1:])
pimage_single_tag.is_safe = True

