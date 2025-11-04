"""
Label Statistics Module
Generates statistics and counts for extracted labels
"""
from typing import List, Dict, Any
from collections import defaultdict
import re
import logging

from ..vision_ai.analyzer import LabelData

logger = logging.getLogger(__name__)


class LabelStatistics:
    """Generate statistics from extracted labels"""

    def __init__(self, labels: List[LabelData]):
        self.labels = labels

    def count_by_equipment_type(self) -> Dict[str, int]:
        """Count labels by equipment type"""
        counts = defaultdict(int)
        for label in self.labels:
            counts[label.equipment_type] += 1
        return dict(sorted(counts.items()))

    def count_by_voltage_class(self) -> Dict[str, int]:
        """Count labels by voltage class"""
        voltage_classes = {
            "Medium Voltage (>600V)": 0,
            "Low Voltage (480V)": 0,
            "Extra Low Voltage (<50V)": 0,
            "Unknown": 0
        }

        for label in self.labels:
            if not label.specs:
                voltage_classes["Unknown"] += 1
                continue

            # Extract voltage value
            if "kV" in label.specs:
                # Medium voltage
                voltage_classes["Medium Voltage (>600V)"] += 1
            elif "480" in label.specs or "277" in label.specs:
                # Low voltage
                voltage_classes["Low Voltage (480V)"] += 1
            elif re.search(r'(\d+)V', label.specs):
                match = re.search(r'(\d+)V', label.specs)
                voltage = int(match.group(1))
                if voltage < 50:
                    voltage_classes["Extra Low Voltage (<50V)"] += 1
                elif voltage > 600:
                    voltage_classes["Medium Voltage (>600V)"] += 1
                else:
                    voltage_classes["Low Voltage (480V)"] += 1
            else:
                voltage_classes["Unknown"] += 1

        return voltage_classes

    def count_by_amperage_range(self) -> Dict[str, int]:
        """Count labels by amperage range"""
        amperage_ranges = {
            "<100A": 0,
            "100-600A": 0,
            "600-2000A": 0,
            ">2000A": 0,
            "Unknown": 0
        }

        for label in self.labels:
            if not label.specs:
                amperage_ranges["Unknown"] += 1
                continue

            # Extract amperage value
            match = re.search(r'(\d+)A', label.specs)
            if match:
                amps = int(match.group(1))
                if amps < 100:
                    amperage_ranges["<100A"] += 1
                elif amps < 600:
                    amperage_ranges["100-600A"] += 1
                elif amps < 2000:
                    amperage_ranges["600-2000A"] += 1
                else:
                    amperage_ranges[">2000A"] += 1
            else:
                amperage_ranges["Unknown"] += 1

        return amperage_ranges

    def count_spare_labels(self) -> int:
        """Count SPARE labels"""
        return sum(1 for label in self.labels if label.is_spare)

    def calculate_total_amperage(self) -> Dict[str, int]:
        """Calculate total amperage by equipment type"""
        totals = defaultdict(int)

        for label in self.labels:
            if not label.specs:
                continue

            match = re.search(r'(\d+)A', label.specs)
            if match:
                amps = int(match.group(1))
                totals[label.equipment_type] += amps

        return dict(sorted(totals.items()))

    def get_connection_summary(self) -> Dict[str, int]:
        """Get summary of connection types"""
        summary = {
            "single_feed": 0,
            "dual_feed": 0,
            "no_connection": 0
        }

        for label in self.labels:
            if label.primary_from and label.alternate_from:
                summary["dual_feed"] += 1
            elif label.fed_from or label.primary_from:
                summary["single_feed"] += 1
            else:
                summary["no_connection"] += 1

        return summary

    def generate_report(self) -> str:
        """Generate comprehensive statistics report"""
        report = []
        report.append("=" * 60)
        report.append("LABEL EXTRACTION STATISTICS")
        report.append("=" * 60)
        report.append(f"Total Labels: {len(self.labels)}")
        report.append(f"Spare Labels: {self.count_spare_labels()}")
        report.append("")

        # Equipment type breakdown
        report.append("Equipment Type Breakdown:")
        report.append("-" * 40)
        for eq_type, count in self.count_by_equipment_type().items():
            report.append(f"  {eq_type:15s}: {count:3d} labels")

        # Total amperage
        report.append("")
        report.append("Total Amperage by Equipment:")
        report.append("-" * 40)
        for eq_type, amps in self.calculate_total_amperage().items():
            report.append(f"  {eq_type:15s}: {amps:6d}A")

        # Voltage classes
        report.append("")
        report.append("Voltage Classification:")
        report.append("-" * 40)
        for voltage_class, count in self.count_by_voltage_class().items():
            if count > 0:
                report.append(f"  {voltage_class:30s}: {count:3d} labels")

        # Amperage ranges
        report.append("")
        report.append("Amperage Ranges:")
        report.append("-" * 40)
        for amp_range, count in self.count_by_amperage_range().items():
            if count > 0:
                report.append(f"  {amp_range:15s}: {count:3d} labels")

        # Connection summary
        report.append("")
        report.append("Connection Summary:")
        report.append("-" * 40)
        conn_summary = self.get_connection_summary()
        report.append(f"  Single Feed  : {conn_summary['single_feed']} labels")
        report.append(f"  Dual Feed    : {conn_summary['dual_feed']} labels")
        report.append(f"  No Connection: {conn_summary['no_connection']} labels")

        report.append("=" * 60)

        return "\n".join(report)
