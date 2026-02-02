# Copyright (c) 2020, nts Technologies and contributors
# License: MIT. See LICENSE

import json

import nts
from nts import _
from nts.model.document import Document
from nts.utils.caching import redis_cache


class InvalidAppOrder(nts.ValidationError):
	pass


class InstalledApplications(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from nts.core.doctype.installed_application.installed_application import InstalledApplication
		from nts.types import DF

		installed_applications: DF.Table[InstalledApplication]
	# end: auto-generated types

	def update_versions(self):
		self.reload_doc_if_required()

		app_wise_setup_details = self.get_app_wise_setup_details()

		self.delete_key("installed_applications")
		for app in nts.utils.get_installed_apps_info():
			has_setup_wizard = 1
			setup_complete = app_wise_setup_details.get(app.get("app_name")) or 0
			if app.get("app_name") in ["nts", "erpnext"] and not setup_complete:
				if app.get("app_name") == "nts" and has_non_admin_user():
					setup_complete = 1

				if app.get("app_name") == "erpnext" and has_company():
					setup_complete = 1

			if app.get("app_name") not in ["nts", "erpnext"]:
				setup_complete = 0
				has_setup_wizard = 0

			self.append(
				"installed_applications",
				{
					"app_name": app.get("app_name"),
					"app_version": app.get("version") or "UNVERSIONED",
					"git_branch": app.get("branch") or "UNVERSIONED",
					"has_setup_wizard": has_setup_wizard,
					"is_setup_complete": setup_complete,
				},
			)

		try:
			savepoint = "update_installed_apps"
			nts.db.savepoint(savepoint)
			self.save()
		except nts.db.DataError:
			nts.db.rollback(save_point=savepoint)
			# Tolerate primary key change on versions during migrate
			self.save(ignore_version=True)

		nts.clear_cache(doctype="System Settings")
		nts.db.set_single_value("System Settings", "setup_complete", nts.is_setup_complete())

	def get_app_wise_setup_details(self):
		"""Get app wise setup details from the Installed Application doctype"""
		return nts._dict(
			nts.get_all(
				"Installed Application",
				fields=["app_name", "is_setup_complete"],
				filters={"has_setup_wizard": 1},
				as_list=True,
			)
		)

	def reload_doc_if_required(self):
		if nts.db.has_column("Installed Application", "is_setup_complete"):
			return

		nts.reload_doc("core", "doctype", "installed_application")
		nts.reload_doc("core", "doctype", "installed_applications")
		nts.reload_doc("integrations", "doctype", "webhook")


def has_non_admin_user():
	if nts.db.has_table("User") and nts.db.get_value(
		"User", {"user_type": "System User", "name": ["not in", ["Administrator", "Guest"]]}
	):
		return True

	return False


def has_company():
	if nts.db.has_table("Company") and nts.get_all("Company", limit=1):
		return True

	return False


@nts.whitelist()
def update_installed_apps_order(new_order: list[str] | str):
	"""Change the ordering of `installed_apps` global

	This list is used to resolve hooks and by default it's order of installation on site.

	Sometimes it might not be the ordering you want, so thie function is provided to override it.
	"""
	nts.only_for("System Manager")

	if isinstance(new_order, str):
		new_order = json.loads(new_order)

	nts.local.request_cache and nts.local.request_cache.clear()
	existing_order = nts.get_installed_apps(_ensure_on_bench=True)

	if set(existing_order) != set(new_order) or not isinstance(new_order, list):
		nts.throw(
			_("You are only allowed to update order, do not remove or add apps."), exc=InvalidAppOrder
		)

	# Ensure nts is always first regardless of user's preference.
	if "nts" in new_order:
		new_order.remove("nts")
	new_order.insert(0, "nts")

	nts.db.set_global("installed_apps", json.dumps(new_order))

	_create_version_log_for_change(existing_order, new_order)


def _create_version_log_for_change(old, new):
	version = nts.new_doc("Version")
	version.ref_doctype = "DefaultValue"
	version.docname = "installed_apps"
	version.data = nts.as_json({"changed": [["current", json.dumps(old), json.dumps(new)]]})
	version.flags.ignore_links = True  # This is a fake doctype
	version.flags.ignore_permissions = True
	version.insert()


@nts.whitelist()
def get_installed_app_order() -> list[str]:
	nts.only_for("System Manager")

	return nts.get_installed_apps(_ensure_on_bench=True)


def get_setup_wizard_completed_apps():
	"""Get list of apps that have completed setup wizard"""
	apps: InstalledApplications = nts.client_cache.get_doc("Installed Applications")
	return [a.app_name for a in apps.installed_applications if a.has_setup_wizard and a.is_setup_complete]


def get_setup_wizard_not_required_apps():
	"""Get list of apps that do not require setup wizard"""
	apps: InstalledApplications = nts.client_cache.get_doc("Installed Applications")
	return [a.app_name for a in apps.installed_applications if not a.has_setup_wizard]


@nts.request_cache
def get_apps_with_incomplete_dependencies(current_app):
	"""Get apps with incomplete dependencies."""
	dependent_apps = ["nts"]

	if apps := nts.get_hooks("required_apps", app_name=current_app):
		dependent_apps.extend(apps)

	parsed_apps = []
	for apps in dependent_apps:
		apps = apps.split("/")
		parsed_apps.extend(apps)

	pending_apps = get_setup_wizard_pending_apps(parsed_apps)

	return pending_apps


def get_setup_wizard_pending_apps(apps=None):
	"""Get list of apps that have completed setup wizard"""

	apps: InstalledApplications = nts.client_cache.get_doc("Installed Applications")
	pending_apps = [
		a.app_name for a in apps.installed_applications if a.has_setup_wizard and not a.is_setup_complete
	]
	if apps:
		pending_apps = [a for a in pending_apps if a in apps]

	return pending_apps
