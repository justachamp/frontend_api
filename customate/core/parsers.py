import io
import json

from django.conf import settings
from rest_framework_json_api import parsers


class JSONAPIBulkParser(parsers.JSONParser):
    media_type = 'application/vnd.api+json'

    def parse(self, stream, media_type=None, parser_context=None):
        data = []
        encoding = parser_context.get('encoding', settings.DEFAULT_CHARSET)
        raw_data = json.loads(stream.read().decode(encoding))

        if isinstance(raw_data['data'], list):

            for single_data in raw_data['data']:
                single_data = {'data': single_data}
                sub_data = self._single_parse(
                    self._dump_data(single_data, encoding),
                    media_type=media_type,
                    parser_context=parser_context
                )
                data.append(sub_data)
        else:
            data = self._single_parse(
                self._dump_data(raw_data, encoding),
                media_type=media_type,
                parser_context=parser_context
            )

        return data

    @staticmethod
    def _dump_data(data, encoding):
        return io.BytesIO(bytes(json.dumps(data), encoding))

    def _single_parse(self, stream, media_type, parser_context=None):
        return super().parse(stream, media_type=media_type, parser_context=parser_context)
