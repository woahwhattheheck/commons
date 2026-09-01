"""ChartTrace Lane D — internal review line (v1.1).

Review does not punish imagination. It kills factual unreliability,
unusable presentation, and unlawful release.
"""

from charttrace.review.dispositions import Disposition, DispositionRecord
from charttrace.review.pipeline import ReviewPipeline, ReviewResult

__all__ = [
    "Disposition",
    "DispositionRecord",
    "ReviewPipeline",
    "ReviewResult",
]

SCHEMA_VERSION = "charttrace.review.v1"
GROUNDING_VERSION = "charttrace.review.grounding.v1"
