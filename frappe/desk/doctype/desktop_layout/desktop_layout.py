# Copyright (c) 2026, nts Technologies and contributors
# For license information, please see license.txt

import json

import nts
from nts.model.document import Document


class DesktopLayout(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from nts.types import DF

		layout: DF.Code | None
		user: DF.Link | None
	# end: auto-generated types

	pass


@nts.whitelist()
def save_layout(user, layout, new_icons):
	if not user:
		user = nts.session.user
	layout = json.loads(layout)
	new_icons = json.loads(new_icons)
	desktop_layout = None
	try:
		desktop_layout = nts.get_doc("Desktop Layout", nts.session.user)
	except nts.DoesNotExistError:
		nts.clear_last_message()
		desktop_layout = nts.new_doc("Desktop Layout")
		desktop_layout.user = nts.session.user

	if layout:
		desktop_layout.layout = json.dumps(layout)
		desktop_layout.save()

	for icon in new_icons:
		desktop_icon = nts.new_doc("Desktop Icon")
		desktop_icon.update(icon)
		desktop_icon.owner = nts.session.user
		desktop_icon.save()

	return {"layout": layout}
