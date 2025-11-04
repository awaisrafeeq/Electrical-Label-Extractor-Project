"""
Label Validation Module
Validates extracted labels for completeness and correctness
"""
from typing import List, Dict, Any
from dataclasses import dataclass
import re
import logging

from ..vision_ai.analyzer import LabelData

logger = logging.getLogger(__name__)


@dataclass
class ValidationError:
    """Represents a validation error"""
    label_index: int
    device_tag: str
    error_type: str
    message: str
    severity: str  # "error", "warning", "info"


class LabelValidator:
    """Validates extracted labels"""

    def __init__(self):
        self.errors = []

    def validate_all(self, labels: List[LabelData]) -> List[ValidationError]:
        """
        Validate all labels and return list of errors

        Args:
            labels: List of LabelData objects

        Returns:
            List of ValidationError objects
        """
        self.errors = []

        for idx, label in enumerate(labels):
            self.validate_device_tag(idx, label)
            self.validate_specs(idx, label)
            self.validate_connections(idx, label, labels)
            self.validate_completeness(idx, label)

        logger.info(f"Validation complete: {len(self.errors)} issues found")
        return self.errors

    def validate_device_tag(self, idx: int, label: LabelData):
        """Validate device tag format"""
        if not label.device_tag:
            self.errors.append(ValidationError(
                label_index=idx,
                device_tag="",
                error_type="missing_device_tag",
                message="Device tag is missing",
                severity="error"
            ))
            return

        # Check basic format: Should have spaces and alphanumeric
        if not re.match(r'^[A-Z0-9\s\-]+$', label.device_tag):
            self.errors.append(ValidationError(
                label_index=idx,
                device_tag=label.device_tag,
                error_type="invalid_device_tag",
                message=f"Device tag contains invalid characters: {label.device_tag}",
                severity="warning"
            ))

        # Check minimum length
        if len(label.device_tag) < 5:
            self.errors.append(ValidationError(
                label_index=idx,
                device_tag=label.device_tag,
                error_type="short_device_tag",
                message=f"Device tag too short: {label.device_tag}",
                severity="warning"
            ))

    def validate_specs(self, idx: int, label: LabelData):
        """Validate voltage/amperage specifications"""
        # SPARE labels may not have specs
        if label.is_spare:
            return

        if not label.specs:
            self.errors.append(ValidationError(
                label_index=idx,
                device_tag=label.device_tag,
                error_type="missing_specs",
                message="Voltage/amperage specifications missing",
                severity="error"
            ))
            return

        # Check for amperage
        if not re.search(r'\d+A', label.specs):
            self.errors.append(ValidationError(
                label_index=idx,
                device_tag=label.device_tag,
                error_type="missing_amperage",
                message=f"Amperage not found in specs: {label.specs}",
                severity="warning"
            ))

        # Check for voltage
        if not re.search(r'\d+(V|kV)', label.specs):
            self.errors.append(ValidationError(
                label_index=idx,
                device_tag=label.device_tag,
                error_type="missing_voltage",
                message=f"Voltage not found in specs: {label.specs}",
                severity="warning"
            ))

    def validate_connections(self, idx: int, label: LabelData, all_labels: List[LabelData]):
        """Validate feeder connections"""
        # Skip SPARE and utility sources
        if label.is_spare:
            return

        # Check if has any connection
        has_connection = (label.fed_from or label.primary_from)

        if not has_connection:
            # Some equipment types don't need connections (e.g., generators, utility sources)
            if label.equipment_type not in ["GENAH", "GENBH", "MVS"]:
                self.errors.append(ValidationError(
                    label_index=idx,
                    device_tag=label.device_tag,
                    error_type="missing_connection",
                    message="No feeder connection specified",
                    severity="warning"
                ))
            return

        # Validate source equipment exists (if not utility)
        source = label.fed_from or label.primary_from
        if source and source.upper() not in ["UTILITY", "GRID", "MAIN"]:
            source_exists = any(
                source in l.device_tag for l in all_labels
            )

            if not source_exists:
                self.errors.append(ValidationError(
                    label_index=idx,
                    device_tag=label.device_tag,
                    error_type="invalid_source",
                    message=f"Source equipment '{source}' not found in diagram",
                    severity="error"
                ))

        # Check for circular references
        if label.fed_from and label.fed_from in label.device_tag:
            self.errors.append(ValidationError(
                label_index=idx,
                device_tag=label.device_tag,
                error_type="circular_reference",
                message="Equipment cannot feed itself",
                severity="error"
            ))

    def validate_completeness(self, idx: int, label: LabelData):
        """Validate label has all required fields"""
        if not label.equipment_type:
            self.errors.append(ValidationError(
                label_index=idx,
                device_tag=label.device_tag,
                error_type="missing_equipment_type",
                message="Equipment type is missing",
                severity="error"
            ))

    def get_summary(self) -> Dict[str, int]:
        """Get summary of validation errors"""
        summary = {
            "total": len(self.errors),
            "errors": len([e for e in self.errors if e.severity == "error"]),
            "warnings": len([e for e in self.errors if e.severity == "warning"]),
            "info": len([e for e in self.errors if e.severity == "info"])
        }
        return summary

    def get_errors_by_type(self) -> Dict[str, int]:
        """Get count of errors by type"""
        error_counts = {}
        for error in self.errors:
            error_counts[error.error_type] = error_counts.get(error.error_type, 0) + 1
        return error_counts
