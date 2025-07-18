"""SCSS Processing Service

This service replaces the monolithic processor.py with a clean, type-safe architecture.
It orchestrates the transformation of legacy SCSS to Site Builder-compatible CSS.
"""

import logging
import time
from pathlib import Path
from typing import Dict, List, Optional

from ...config import AutoSBMSettings
from .exceptions import ScssProcessingException, ScssValidationException
from .models import (
    ScssProcessingConfig,
    ScssProcessingError,
    ScssProcessingMode,
    ScssProcessingResult,
    ScssTransformationContext,
    ScssTransformationStep,
    ScssValidationResult,
)
from .transformers import (
    ContentCleaner,
    FunctionTransformer,
    ImportRemover,
    MixinTransformer,
    PathTransformer,
    VariableTransformer,
)
from .validator import ScssValidator

logger = logging.getLogger(__name__)


class ScssProcessingService:
    """
    Core SCSS processing service that orchestrates theme transformations.
    
    This service replaces the monolithic SCSSProcessor with a clean, type-safe interface
    that coordinates with specialized transformer modules.
    """

    def __init__(self, settings: AutoSBMSettings):
        self.settings = settings
        self.validator = ScssValidator()

        # Initialize transformers
        self._transformers = {
            ScssTransformationStep.VARIABLE_PROCESSING: VariableTransformer(),
            ScssTransformationStep.MIXIN_CONVERSION: MixinTransformer(),
            ScssTransformationStep.FUNCTION_CONVERSION: FunctionTransformer(),
            ScssTransformationStep.PATH_CONVERSION: PathTransformer(),
            ScssTransformationStep.IMPORT_REMOVAL: ImportRemover(),
            ScssTransformationStep.CLEANUP: ContentCleaner()
        }

        logger.info("SCSS Processing Service initialized")

    async def process_scss_content(
        self,
        content: str,
        config: ScssProcessingConfig,
        source_file: Optional[Path] = None
    ) -> ScssProcessingResult:
        """
        Process SCSS content according to configuration.
        
        Args:
            content: SCSS content to process
            config: Processing configuration
            source_file: Optional source file path
            
        Returns:
            ScssProcessingResult with transformation outcome
        """
        start_time = time.time()

        try:
            # Validate input
            if not content.strip():
                raise ScssValidationException("Cannot process empty SCSS content")

            # Check file size limits
            content_size = len(content.encode("utf-8"))
            max_size = config.max_file_size_mb * 1024 * 1024
            if content_size > max_size:
                raise ScssProcessingException(
                    f"Content size ({content_size} bytes) exceeds limit ({max_size} bytes)"
                )

            # Create processing context
            context = ScssTransformationContext(
                source_content=content,
                source_file=source_file
            )

            # Execute processing pipeline
            context = await self._execute_processing_pipeline(context, config)

            # Validate output if requested
            validation_result = None
            if config.validate_syntax:
                validation_result = await self.validator.validate_scss_content(
                    context.current_content,
                    test_compilation=config.test_compilation
                )
                context.syntax_valid = validation_result.is_valid
                context.compilation_successful = validation_result.compilation_successful

            # Build result
            processing_time = time.time() - start_time
            context.processing_time_seconds = processing_time

            result = ScssProcessingResult(
                success=True,
                output_content=context.current_content,
                context=context,
                input_size_bytes=len(content.encode("utf-8")),
                output_size_bytes=len(context.current_content.encode("utf-8")),
                processing_time_seconds=processing_time,
                variables_converted=len(context.variables),
                mixins_converted=len(context.mixins),
                functions_converted=len(context.functions),
                imports_removed=len(context.imports)
            )

            # Add validation errors if any
            if validation_result and not validation_result.is_valid:
                result.syntax_errors = validation_result.errors
                result.warnings = validation_result.warnings

                if config.strict_mode:
                    result.success = False

            logger.info(f"SCSS processing completed in {processing_time:.2f}s")
            return result

        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"SCSS processing failed: {e}")

            return ScssProcessingResult(
                success=False,
                processing_time_seconds=processing_time,
                syntax_errors=[ScssProcessingError(
                    error_type="processing_error",
                    message=str(e),
                    severity="error"
                )]
            )

    async def process_scss_file(
        self,
        file_path: Path,
        config: ScssProcessingConfig,
        output_file: Optional[Path] = None
    ) -> ScssProcessingResult:
        """
        Process an SCSS file.
        
        Args:
            file_path: Path to SCSS file
            config: Processing configuration
            output_file: Optional output file path
            
        Returns:
            ScssProcessingResult with transformation outcome
        """
        try:
            # Validate file path
            if not file_path.exists():
                raise ScssProcessingException(f"SCSS file not found: {file_path}")

            if not file_path.is_file():
                raise ScssProcessingException(f"Path is not a file: {file_path}")

            # Check file size
            file_size = file_path.stat().st_size
            max_size = config.max_file_size_mb * 1024 * 1024
            if file_size > max_size:
                raise ScssProcessingException(
                    f"File size ({file_size} bytes) exceeds limit ({max_size} bytes)"
                )

            # Read file content
            content = file_path.read_text(encoding="utf-8")

            # Process content
            result = await self.process_scss_content(content, config, file_path)

            # Write output file if specified and processing succeeded
            if output_file and result.success and result.output_content:
                await self._write_output_file(output_file, result.output_content)
                result.generated_files.append(output_file)

                # Create backup if requested
                if config.enable_caching:
                    backup_file = self._create_backup_file(file_path)
                    if backup_file:
                        result.backup_files.append(backup_file)

            return result

        except Exception as e:
            logger.error(f"Failed to process SCSS file {file_path}: {e}")
            return ScssProcessingResult(
                success=False,
                syntax_errors=[ScssProcessingError(
                    error_type="file_processing_error",
                    message=str(e),
                    severity="error"
                )]
            )

    async def validate_scss_content(
        self,
        content: str,
        test_compilation: bool = True
    ) -> ScssValidationResult:
        """
        Validate SCSS content without transformation.
        
        Args:
            content: SCSS content to validate
            test_compilation: Whether to test compilation
            
        Returns:
            ScssValidationResult with validation outcome
        """
        return await self.validator.validate_scss_content(content, test_compilation)

    async def get_processing_preview(
        self,
        content: str,
        config: ScssProcessingConfig
    ) -> Dict[str, any]:
        """
        Get a preview of what processing would do without actually transforming.
        
        Args:
            content: SCSS content to analyze
            config: Processing configuration
            
        Returns:
            Dictionary with preview information
        """
        try:
            context = ScssTransformationContext(source_content=content)

            # Extract elements without transforming
            if config.convert_variables:
                context = await self._transformers[ScssTransformationStep.VARIABLE_PROCESSING].extract_elements(context)

            if config.convert_mixins:
                context = await self._transformers[ScssTransformationStep.MIXIN_CONVERSION].extract_elements(context)

            if config.convert_functions:
                context = await self._transformers[ScssTransformationStep.FUNCTION_CONVERSION].extract_elements(context)

            if config.remove_imports:
                context = await self._transformers[ScssTransformationStep.IMPORT_REMOVAL].extract_elements(context)

            return {
                "variables_found": len(context.variables),
                "mixins_found": len(context.mixins),
                "functions_found": len(context.functions),
                "imports_found": len(context.imports),
                "estimated_output_size": len(content) * 0.8,  # Rough estimate
                "processing_steps": [step.value for step in self._get_processing_steps(config)]
            }

        except Exception as e:
            logger.error(f"Failed to generate processing preview: {e}")
            return {"error": str(e)}

    async def _execute_processing_pipeline(
        self,
        context: ScssTransformationContext,
        config: ScssProcessingConfig
    ) -> ScssTransformationContext:
        """Execute the complete processing pipeline"""

        processing_steps = self._get_processing_steps(config)

        for step in processing_steps:
            try:
                transformer = self._transformers[step]
                context = await transformer.transform(context)
                context.add_transformation(step.value)

                logger.debug(f"Completed transformation step: {step.value}")

            except Exception as e:
                logger.error(f"Transformation step {step.value} failed: {e}")
                if config.strict_mode:
                    raise ScssProcessingException(f"Pipeline failed at {step.value}: {e}")
                # Continue with next step in non-strict mode

        return context

    def _get_processing_steps(self, config: ScssProcessingConfig) -> List[ScssTransformationStep]:
        """Determine processing steps based on configuration"""
        steps = []

        if config.mode == ScssProcessingMode.VALIDATION_ONLY:
            return [ScssTransformationStep.VALIDATION]

        if config.mode == ScssProcessingMode.VARIABLES_ONLY:
            return [ScssTransformationStep.VARIABLE_PROCESSING, ScssTransformationStep.CLEANUP]

        if config.mode == ScssProcessingMode.MIXINS_ONLY:
            return [ScssTransformationStep.MIXIN_CONVERSION, ScssTransformationStep.CLEANUP]

        # Full processing pipeline
        if config.convert_variables:
            steps.append(ScssTransformationStep.VARIABLE_PROCESSING)

        if config.convert_image_paths:
            steps.append(ScssTransformationStep.PATH_CONVERSION)

        if config.convert_functions:
            steps.append(ScssTransformationStep.FUNCTION_CONVERSION)

        if config.convert_mixins:
            steps.append(ScssTransformationStep.MIXIN_CONVERSION)

        if config.remove_imports:
            steps.append(ScssTransformationStep.IMPORT_REMOVAL)

        if config.validate_syntax:
            steps.append(ScssTransformationStep.VALIDATION)

        # Always cleanup at the end
        steps.append(ScssTransformationStep.CLEANUP)

        return steps

    async def _write_output_file(self, output_file: Path, content: str) -> None:
        """Write output content to file safely"""
        try:
            # Ensure parent directory exists
            output_file.parent.mkdir(parents=True, exist_ok=True)

            # Write content atomically
            temp_file = output_file.with_suffix(output_file.suffix + ".tmp")
            temp_file.write_text(content, encoding="utf-8")
            temp_file.rename(output_file)

            logger.info(f"Output written to: {output_file}")

        except Exception as e:
            logger.error(f"Failed to write output file {output_file}: {e}")
            raise ScssProcessingException(f"Failed to write output: {e}")

    def _create_backup_file(self, original_file: Path) -> Optional[Path]:
        """Create backup of original file"""
        try:
            backup_file = original_file.with_suffix(original_file.suffix + ".backup")
            backup_file.write_text(original_file.read_text(encoding="utf-8"), encoding="utf-8")
            logger.info(f"Backup created: {backup_file}")
            return backup_file

        except Exception as e:
            logger.warning(f"Failed to create backup for {original_file}: {e}")
            return None

    def get_processing_statistics(self) -> Dict[str, any]:
        """Get processing statistics and performance metrics"""
        return {
            "transformers_available": len(self._transformers),
            "processing_steps": [step.value for step in ScssTransformationStep],
            "supported_features": {
                "variable_conversion": True,
                "mixin_conversion": True,
                "function_conversion": True,
                "path_conversion": True,
                "import_removal": True,
                "syntax_validation": True,
                "compilation_testing": True
            }
        }
