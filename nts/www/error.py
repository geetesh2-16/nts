# Copyright (c) 2015, nts Technologies Pvt. Ltd. and Contributors
# License: MIT. See LICENSE
import nts
from nts import _
from nts.utils.response import is_traceback_allowed

no_cache = 1


def get_context(context):
	if nts.flags.in_migrate:
		return

	if not context.title:
		context.title = _("Server Error")
	if not context.message:
		context.message = _("There was an error building this page")

	return {
		"error": nts.get_traceback().replace("<", "&lt;").replace(">", "&gt;")
		if is_traceback_allowed()
		else ""
	}
