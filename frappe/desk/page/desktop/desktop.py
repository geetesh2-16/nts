import sys

import nts
from nts.desk.doctype.desktop_icon.desktop_icon import get_desktop_icons


def get_context(context):
	if nts.session.user == "Guest":
		nts.local.flags.redirect_location = "/app"
		raise nts.Redirect
	brand_logo = None
	brand_logo = nts.get_single_value("Navbar Settings", "app_logo")
	if not brand_logo:
		brand_logo = nts.get_hooks("app_logo_url", app_name="nts")[0]
	context.brand_logo = brand_logo
	try:
		context.desktop_layout = nts.get_doc("Desktop Layout", nts.session.user).layout or {}
	except nts.DoesNotExistError:
		nts.clear_last_message()
		context.desktop_layout = {}
	return context
