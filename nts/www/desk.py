# Copyright (c) 2015, nts Technologies Pvt. Ltd. and Contributors
# License: MIT. See LICENSE
import os

no_cache = 1

import json
import re
from urllib.parse import urlencode

import nts
import nts.sessions
from nts import _
from nts.utils.jinja_globals import is_rtl

SCRIPT_TAG_PATTERN = re.compile(r"\<script[^<]*\</script\>")
CLOSING_SCRIPT_TAG_PATTERN = re.compile(r"</script\>")


def get_context(context):
	if nts.session.user == "Guest":
		nts.response["status_code"] = 403
		nts.msgprint(_("Log in to access this page."))
		nts.redirect(f"/login?{urlencode({'redirect-to': nts.request.path})}")

	elif nts.session.data.user_type == "Website User":
		nts.throw(_("You are not permitted to access this page."), nts.PermissionError)

	try:
		boot = nts.sessions.get()
	except Exception as e:
		raise nts.SessionBootFailed from e

	# this needs commit
	csrf_token = nts.sessions.get_csrf_token()

	hooks = nts.get_hooks()
	app_include_js = hooks.get("app_include_js", []) + nts.conf.get("app_include_js", [])
	app_include_css = hooks.get("app_include_css", []) + nts.conf.get("app_include_css", [])
	app_include_icons = hooks.get("app_include_icons", [])

	if nts.get_system_settings("enable_telemetry") and os.getenv("nts_SENTRY_DSN"):
		app_include_js.append("sentry.bundle.js")

	context.update(
		{
			"no_cache": 1,
			"build_version": nts.utils.get_build_version(),
			"app_include_js": app_include_js,
			"app_include_css": app_include_css,
			"app_include_icons": app_include_icons,
			"layout_direction": "rtl" if is_rtl() else "ltr",
			"lang": nts.local.lang,
			"sounds": hooks["sounds"],
			"boot": boot,
			"desk_theme": boot.get("desk_theme") or "Light",
			"csrf_token": csrf_token,
			"google_analytics_id": nts.conf.get("google_analytics_id"),
			"google_analytics_anonymize_ip": nts.conf.get("google_analytics_anonymize_ip"),
			"app_name": (
				nts.get_website_settings("app_name") or nts.get_system_settings("app_name") or "nts"
			),
		}
	)

	return context
