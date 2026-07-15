"""Application-specific errors mapped to stable API error codes."""


class ViewerError(Exception):
    # code / status_code を各サブクラスへ置き、View 側は共通処理だけで返せるようにする。
    code = "viewer_error"
    status_code = 400

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class ValidationError(ViewerError):
    code = "validation_error"
    status_code = 400


class SecurityError(ViewerError):
    code = "security_error"
    status_code = 400


class UnsupportedFormatError(ViewerError):
    code = "unsupported_format"
    status_code = 400


class FetchError(ViewerError):
    code = "fetch_error"
    status_code = 502


class ConversionError(ViewerError):
    code = "conversion_error"
    status_code = 500


class NotFoundError(ViewerError):
    code = "not_found"
    status_code = 404
