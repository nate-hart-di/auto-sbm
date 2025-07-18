"""Custom exceptions for SCSS processing operations"""

from typing import List, Optional


class ScssProcessingException(Exception):
    """Base exception for SCSS processing operations"""

    def __init__(
        self,
        message: str,
        line_number: Optional[int] = None,
        file_path: Optional[str] = None
    ):
        self.message = message
        self.line_number = line_number
        self.file_path = file_path
        super().__init__(self._format_message())

    def _format_message(self) -> str:
        """Format error message with location information"""
        parts = [self.message]

        if self.file_path:
            parts.append(f"File: {self.file_path}")

        if self.line_number:
            parts.append(f"Line: {self.line_number}")

        return " | ".join(parts)


class ScssValidationException(ScssProcessingException):
    """Exception for SCSS validation failures"""

    def __init__(
        self,
        message: str,
        validation_errors: Optional[List[str]] = None,
        **kwargs
    ):
        self.validation_errors = validation_errors or []
        super().__init__(message, **kwargs)


class ScssMixinException(ScssProcessingException):
    """Exception for mixin conversion failures"""

    def __init__(
        self,
        message: str,
        mixin_name: Optional[str] = None,
        **kwargs
    ):
        self.mixin_name = mixin_name
        if mixin_name:
            message = f"Mixin '{mixin_name}': {message}"
        super().__init__(message, **kwargs)


class ScssVariableException(ScssProcessingException):
    """Exception for variable conversion failures"""

    def __init__(
        self,
        message: str,
        variable_name: Optional[str] = None,
        **kwargs
    ):
        self.variable_name = variable_name
        if variable_name:
            message = f"Variable '{variable_name}': {message}"
        super().__init__(message, **kwargs)


class ScssFunctionException(ScssProcessingException):
    """Exception for function conversion failures"""

    def __init__(
        self,
        message: str,
        function_name: Optional[str] = None,
        **kwargs
    ):
        self.function_name = function_name
        if function_name:
            message = f"Function '{function_name}': {message}"
        super().__init__(message, **kwargs)


class ScssCompilationException(ScssProcessingException):
    """Exception for SCSS compilation failures"""

    def __init__(
        self,
        message: str,
        compilation_output: Optional[str] = None,
        **kwargs
    ):
        self.compilation_output = compilation_output
        super().__init__(message, **kwargs)
