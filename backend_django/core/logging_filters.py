from core.logging_context import request_id_ctx


class RequestIdFilter:
    def filter(self, record):
        record.request_id = request_id_ctx.get()
        return True
