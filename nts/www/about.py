# Copyright (c) 2015, nts Technologies Pvt. Ltd. and Contributors
# License: MIT. See LICENSE

import nts

sitemap = 1


def get_context(context):
	context.doc = nts.get_cached_doc("About Us Settings")
	if context.doc.is_disabled:
		nts.local.flags.redirect_location = "/404"
		raise nts.Redirect
	return context
