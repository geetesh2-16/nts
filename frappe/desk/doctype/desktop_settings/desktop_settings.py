# Copyright (c) 2025, nts Technologies and contributors
# For license information, please see license.txt

# import nts
from nts.model.document import Document


class DesktopSettings(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from nts.types import DF

		icon_style: DF.Literal["Subtle", "Solid"]
	# end: auto-generated types

	pass
