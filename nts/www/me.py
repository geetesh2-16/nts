# Copyright (c) 2015, nts Technologies Pvt. Ltd. and Contributors
# License: MIT. See LICENSE

import nts
from nts import _
from nts.utils.user import is_portal_user

no_cache = 1


def get_context(context):
	if nts.session.user == "Guest":
		nts.throw(_("You need to be logged in to access this page"), nts.PermissionError)

	context.current_user = nts.get_doc("User", nts.session.user)
	context.show_sidebar = False
	context.is_portal_user = is_portal_user()
