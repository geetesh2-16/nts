# Copyright (c) 2025, nts Technologies and contributors
# For license information, please see license.txt

import nts
from nts.model.document import Document


class WorkflowTransitionTask(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from nts.types import DF

		asynchronous: DF.Check
		enabled: DF.Check
		link: DF.DynamicLink | None
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		task: DF.Literal[None]
	# end: auto-generated types

	pass
