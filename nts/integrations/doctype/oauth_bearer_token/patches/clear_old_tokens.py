from contextlib import suppress

from nts.core.doctype.log_settings.log_settings import clear_log_table


def execute():
	"""Clear old tokens"""
	with suppress(Exception):
		clear_log_table("OAuth Bearer Token")
