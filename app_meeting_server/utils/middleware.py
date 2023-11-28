# -*- coding: utf-8 -*-
# @Time    : 2023/11/28 15:22
# @Author  : Tom_zc
# @FileName: middleware.py
# @Software: PyCharm
import logging
from django.http.response import HttpResponseBase
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger("log")


class MyMiddleware(MiddlewareMixin):
    def process_response(self, _, response):
        logger.info("1.---------------------------")
        if isinstance(response, HttpResponseBase):
            logger.info("2.---------------------------")
            response["X-XSS-Protection"] = "1; mode=block"
            response["X-Frame-Options"] = "DENY"
            response["X-Content-Type-Options"] = "nosniff"
            response["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
            response["Content-Security-Policy"] = "script-src 'self'; object-src 'none'; frame-src 'none'"
            response["Cache-Control"] = "no-cache,no-store,must-revalidate"
            response["Pragma"] = "no-cache"
            response["Expires"] = 0
            response["Referrer-Policy"] = "no-referrer"
