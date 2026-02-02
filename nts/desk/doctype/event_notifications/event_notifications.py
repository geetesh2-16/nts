# Copyright (c) 2025, nts Technologies and contributors
# For license information, please see license.txt

# import nts
from nts.model.document import Document


class EventNotifications(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from nts.types import DF

		before: DF.Int
		interval: DF.Literal[None]
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		time: DF.Time | None
		type: DF.Literal["Notification", "Email"]
	# end: auto-generated types

	pass
