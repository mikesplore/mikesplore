import json
import base64

from .client import client
from .prompts import SYSTEM, EXTRACT_SYSTEM, CV_TAILOR_SYSTEM
from .admin_tools import ADMIN_TOOLS, execute_admin_tool, extract_admin_operation, extract_entry, extract_job_description_from_image, extract_profile_update, extract_update, propose_role_policies, tailor_cv
from .public_tools import answer, present_admin_result
