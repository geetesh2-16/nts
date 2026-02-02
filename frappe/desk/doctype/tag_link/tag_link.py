# Copyright (c) 2019, nts Technologies and contributors
# License: MIT. See LICENSE

import nts
from nts.model.document import Document


class TagLink(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from nts.types import DF

		document_name: DF.DynamicLink | None
		document_type: DF.Link | None
		tag: DF.Link | None
		title: DF.Data | None

	# end: auto-generated types

	def clear_cache(self):
		super().clear_cache()
		if has_tags(self.document_type):
			nts.client_cache.delete_value(f"doctype_has_tags::{self.document_type}")


def on_doctype_update():
	nts.db.add_index("Tag Link", ["document_type", "document_name"])


def has_tags(doctype: str):
	"""Short circuit checks for tags by first checking if users even uses tags"""

	def check_db():
		return nts.db.exists("Tag Link", {"document_type": doctype})

	return nts.client_cache.get_value(f"doctype_has_tags::{doctype}", generator=check_db)
