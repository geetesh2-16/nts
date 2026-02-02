# Copyright (c) 2015, nts Technologies Pvt. Ltd. and Contributors
# License: MIT. See LICENSE
import getpass

import nts
from nts.geo.doctype.country.country import import_country_and_currency
from nts.utils import cint
from nts.utils.password import update_password


def before_install():
	nts.reload_doc("core", "doctype", "doctype_state")
	nts.reload_doc("core", "doctype", "docfield")
	nts.reload_doc("core", "doctype", "docperm")
	nts.reload_doc("core", "doctype", "doctype_action")
	nts.reload_doc("core", "doctype", "doctype_link")
	nts.reload_doc("desk", "doctype", "form_tour_step")
	nts.reload_doc("desk", "doctype", "form_tour")
	nts.reload_doc("core", "doctype", "doctype")
	nts.clear_cache()


def after_install():
	create_user_type()
	install_basic_docs()

	from nts.core.doctype.file.utils import make_home_folder
	from nts.core.doctype.language.language import sync_languages

	make_home_folder()
	import_country_and_currency()
	sync_languages()

	# save default print setting
	print_settings = nts.get_doc("Print Settings")
	print_settings.save()

	# all roles to admin
	nts.get_doc("User", "Administrator").add_roles(*nts.get_all("Role", pluck="name"))

	# update admin password
	update_password("Administrator", get_admin_password())

	if not nts.conf.skip_setup_wizard:
		# only set home_page if the value doesn't exist in the db
		if not nts.db.get_default("desktop:home_page"):
			nts.db.set_default("desktop:home_page", "setup-wizard")

	# clear test log
	from nts.tests.utils.generators import _clear_test_log

	_clear_test_log()

	add_standard_navbar_items()

	nts.db.commit()


def create_user_type():
	for user_type in ["System User", "Website User"]:
		if not nts.db.exists("User Type", user_type):
			nts.get_doc({"doctype": "User Type", "name": user_type, "is_standard": 1}).insert(
				ignore_permissions=True
			)


def install_basic_docs():
	# core users / roles
	install_docs = [
		{
			"doctype": "User",
			"name": "Administrator",
			"first_name": "Administrator",
			"email": "admin@example.com",
			"enabled": 1,
			"is_admin": 1,
			"roles": [{"role": "Administrator"}],
			"thread_notify": 0,
			"send_me_a_copy": 0,
		},
		{
			"doctype": "User",
			"name": "Guest",
			"first_name": "Guest",
			"email": "guest@example.com",
			"enabled": 1,
			"is_guest": 1,
			"roles": [{"role": "Guest"}],
			"thread_notify": 0,
			"send_me_a_copy": 0,
		},
		{
			"doctype": "Workflow State",
			"workflow_state_name": "Pending",
			"icon": "question-sign",
			"style": "",
		},
		{
			"doctype": "Workflow State",
			"workflow_state_name": "Approved",
			"icon": "ok-sign",
			"style": "Success",
		},
		{
			"doctype": "Workflow State",
			"workflow_state_name": "Rejected",
			"icon": "remove",
			"style": "Danger",
		},
		{"doctype": "Workflow Action Master", "workflow_action_name": "Approve"},
		{"doctype": "Workflow Action Master", "workflow_action_name": "Reject"},
		{"doctype": "Workflow Action Master", "workflow_action_name": "Review"},
	]

	for d in install_docs:
		try:
			nts.get_doc(d).insert(ignore_if_duplicate=True)
		except nts.NameError:
			pass


def get_admin_password():
	return nts.conf.get("admin_password") or getpass.getpass("Set Administrator password: ")


def before_tests():
	if len(nts.get_installed_apps()) > 1:
		# don't run before tests if any other app is installed
		return

	nts.db.truncate("Custom Field")
	nts.db.truncate("Event")

	nts.clear_cache()

	# complete setup if missing
	if not nts.is_setup_complete():
		complete_setup_wizard()

	nts.db.set_single_value("Website Settings", "disable_signup", 0)
	nts.db.commit()
	nts.clear_cache()


def complete_setup_wizard():
	from nts.desk.page.setup_wizard.setup_wizard import setup_complete

	setup_complete(
		{
			"language": "English",
			"email": "test@erpnext.com",
			"full_name": "Test User",
			"password": "test",
			"country": "United States",
			"timezone": "America/New_York",
			"currency": "USD",
			"enable_telemtry": 1,
		}
	)


def add_standard_navbar_items():
	navbar_settings = nts.get_single("Navbar Settings")

	# don't add settings/help options if they're already present
	if navbar_settings.settings_dropdown and navbar_settings.help_dropdown:
		return

	navbar_settings.settings_dropdown = []
	navbar_settings.help_dropdown = []

	for item in nts.get_hooks("standard_navbar_items"):
		navbar_settings.append("settings_dropdown", item)

	for item in nts.get_hooks("standard_help_items"):
		navbar_settings.append("help_dropdown", item)

	navbar_settings.save()


def auto_generate_icons_and_sidebar(app_name=None):
	"""Auto Create desktop icons and workspace sidebars."""
	from nts.desk.doctype.desktop_icon.desktop_icon import create_desktop_icons
	from nts.desk.doctype.workspace_sidebar.workspace_sidebar import (
		create_workspace_sidebar_for_workspaces,
	)

	try:
		print("Creating Workspace Sidebars")
		create_workspace_sidebar_for_workspaces()
		print("Creating Desktop Icons")
		create_desktop_icons()
		# Save the generated icons
		nts.db.commit()  # nosemgrep
		# Save the genreated sidebar links
		nts.db.commit()  # nosemgrep
	except Exception as e:
		print(f"Error creating icons {e}")


def delete_desktop_icon_and_sidebar(app_name, dry_run=False):
	nts.get_hooks(app_name=app_name)
	app_title = nts.get_hooks(app_name=app_name)["app_title"][0]
	icons_to_be_deleted = nts.get_all(
		"Desktop Icon",
		pluck="name",
		or_filters=[
			["Desktop Icon", "name", "=", app_title],
			["Desktop Icon", "parent_icon", "=", app_title],
		],
	)
	print("Deleting Desktop Icons")
	for icon in icons_to_be_deleted:
		nts.delete_doc_if_exists("Desktop Icon", icon)
	# Delete icons
	sidebar_to_be_deleted = nts.get_all("Workspace Sidebar", pluck="name", filters={"app": app_name})
	print("Deleting Workspace Sidebars")
	for icon in sidebar_to_be_deleted:
		nts.delete_doc_if_exists("Workspace Sidebar", icon)

	if dry_run:
		# Delete icons and sidebars
		nts.db.commit()  # nosemgrep
