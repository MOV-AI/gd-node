"""
   Copyright (C) Mov.ai  - All Rights Reserved
   Unauthorized copying of this file, via any medium is strictly prohibited
   Proprietary and confidential

   Developers:
   - Telmo Martinho (telmo.martinho@mov.ai) - 2020
   
   Usage:

    from libraries import Metrics
    metrics_a = Metrics(<name>)

    metrics_a.add(<value>, tags=[<string>, <string>,...])
    -- or --
    metrics_a.log(<value>, tags=[<string>, <string>,...])

"""
import http.client
import json
import logging
import logging.handlers
import os
import re
import uuid
from urllib.parse import urlparse

import requests

from movai_core_shared.logger import Log


class HealthNodeHandler(logging.handlers.HTTPHandler):
    def __init__(self, url):
        logging.Handler.__init__(self)

        parsed_uri = urlparse(url)

        self.host = parsed_uri.netloc
        self.url = parsed_uri.path
        self.method = "POST"
        self.secure = False
        self.credentials = False

    def emit(self, record):
        """
        Emit a record.
        Send the record to the HealthNode API
        """
        try:
            host = self.host
            port = None

            i = host.find(":")
            if i >= 0:
                port = host[i + 1 :]
                host = host[:i]

            conn = http.client.HTTPConnection(host, port=port)

            # Log data
            data = self.mapLogRecord(record)
            data = json.dumps(data)

            headers = {
                "Content-type": "application/json",
                "Content-length": str(len(data)),
            }
            conn.request(self.method, self.url, data, headers)
            conn.getresponse()  # can't do anything with the result
        except Exception:
            self.handleError(record)


class Metrics:
    def __init__(self):
        """
        Metrics
        """

        _log_host = os.environ.get("LOG_HTTP_HOST", "http://health-node:8081")
        _host_http_log_handler = f"{_log_host}/metrics"

        logging.raiseExceptions = False

        # Create custom loggers
        # Generate uuid name to not conflict with existing logger channels
        self._logger = logging.getLogger(str(uuid.uuid4()))

        _handler_name = "health_node_handler"
        health_node_handler = HealthNodeHandler(url=_host_http_log_handler)
        health_node_handler.name = _handler_name
        health_node_handler.setLevel(logging.DEBUG)
        self._logger.addHandler(health_node_handler)  # HEALTH NODE (influxdb)

        self._logger.setLevel(logging.INFO)

        self._tag_service = os.getenv("HOSTNAME")

    def _log(self, name, **kwargs):
        """Add Log"""

        options = {
            "name": name,
            "fields": {**kwargs},
            "tags": {"service": self._tag_service},
        }

        # Call logger
        self._logger.info("metrics", options)  # If getattr by level fails, store log as info

    @staticmethod
    def get_metrics(name=None, limit=1000, offset=0, tags=None, pagination=False):
        """Get Metrics from HealthNode"""

        _metrics_host = os.environ.get("LOG_HTTP_HOST", "http://health-node:8081")
        url = f"{_metrics_host}/metrics"

        params = {
            "name": name,
            "limit": Metrics.validate_limit(limit),
            "offset": Metrics.validate_limit(offset),
        }

        # If invalid name raise ValueError
        Metrics.validate_name(name)

        if tags:
            params["tags"] = Metrics.validate_tags(tags)

        try:
            response = requests.get(url, params=params, timeout=5)
            response.raise_for_status()
        except Exception as e:
            raise e

        try:
            content = response.json()
        except Exception as e:
            logger = Log.get_logger("merrtix")
            logger.error(message=str(e))
            return []
        else:
            return content if pagination else content.get("data", [])

    @staticmethod
    def validate_name(value):
        if value and not re.search(r"[a-zA-Z0-9-_.]+", value):
            raise ValueError("invalid name")
        return value

    @staticmethod
    def validate_tags(value: str):
        return value

    @staticmethod
    def validate_limit(value):
        try:
            val = int(value)
        except ValueError:
            raise ValueError("invalid limit/offset value")
        return val

    @staticmethod
    def validate_fields(value):
        if not value:
            raise ValueError("at least one field is required")

        try:
            value = [] if value is None else value
            tags = ",".join(value)
        except ValueError:
            raise ValueError("invalid tags value")
        return tags

    @staticmethod
    def validate_message(value):
        return value

    @staticmethod
    def _find_between(s, start, end):
        return (s.split(start))[1].split(end)[0]

    @staticmethod
    def _filter_data(*args, **kwargs):
        # Get message stf from args or kwargs
        name = args[0] if args else kwargs.get("name", "")

        # Search and remove fields
        if "name" in kwargs:
            del kwargs["name"]

        return name

    def add(self, *args, **kwargs):
        name = self._filter_data(*args, **kwargs)
        self.validate_name(name)
        self.validate_fields(kwargs)
        self._log(name=name, **kwargs)
