import nts
from nts.utils import get_app_version, get_nts_version

from .client import capture, is_enabled


def capture_app_heartbeat(app):
	if not should_capture():
		return

	if app and app != "nts":
		capture(
			event_name="app_heartbeat",
			site=nts.local.site,
			app=app,
			properties={
				"app_version": get_app_version(app),
				"nts_version": get_nts_version(),
			},
			interval="6h",
		)


def should_capture():
	if not is_enabled() or nts.session.user in nts.STANDARD_USERS:
		return False

	status_code = nts.response.http_status_code or 0
	if status_code and not (200 <= status_code < 300):
		return False

	return True
