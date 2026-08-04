"""AWS per-service scanners."""

from .cloudtrail import CloudTrailScanner
from .cloudwatch import CloudWatchScanner
from .config import ConfigScanner
from .ec2 import EC2Scanner
from .ecr import ECRScanner
from .eks import EKSScanner
from .elb import ELBScanner
from .guardduty import GuardDutyScanner
from .iam import IAMScanner
from .kms import KMSScanner
from .lambda_scanner import LambdaScanner
from .rds import RDSScanner
from .s3 import S3Scanner
from .securityhub import SecurityHubScanner
from .vpc import VPCScanner

ALL_SCANNERS = [
    EC2Scanner(), S3Scanner(), IAMScanner(), RDSScanner(), VPCScanner(),
    EKSScanner(), ELBScanner(), LambdaScanner(), CloudTrailScanner(),
    CloudWatchScanner(), SecurityHubScanner(), GuardDutyScanner(),
    KMSScanner(), ECRScanner(), ConfigScanner(),
]
