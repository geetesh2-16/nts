# Copyright (c) 2018, nts Technologies Pvt. Ltd. and Contributors
# License: MIT. See LICENSE

import nts

common_default_keys = ["__default", "__global"]

doctypes_for_mapping = {
	"Assignment Rule",
	"Milestone Tracker",
	"Document Naming Rule",
}


def get_doctype_map_key(doctype, name="*") -> str:
	return nts.scrub(doctype) + f"_map::{name}"


doctype_map_keys = tuple(map(get_doctype_map_key, doctypes_for_mapping))

bench_cache_keys = ("assets_json",)

global_cache_keys = (
	"app_hooks",
	"installed_apps",
	"all_apps",
	"app_modules",
	"installed_app_modules",
	"module_app",
	"module_installed_app",
	"system_settings",
	"scheduler_events",
	"time_zone",
	"webhooks",
	"active_domains",
	"active_modules",
	"assignment_rule",
	"server_script_map",
	"wkhtmltopdf_version",
	"domain_restricted_doctypes",
	"domain_restricted_pages",
	"information_schema:counts",
	"db_tables",
	"server_script_autocompletion_items",
	*doctype_map_keys,
)

user_cache_keys = (
	"bootinfo",
	"user_recent",
	"roles",
	"user_doc",
	"lang",
	"defaults",
	"user_permissions",
	"home_page",
	"linked_with",
	"desktop_icons",
	"portal_menu_items",
	"user_perm_can_read",
	"has_role:Page",
	"has_role:Report",
	"desk_sidebar_items",
	"contacts",
)

doctype_cache_keys = (
	"last_modified",
	"linked_doctypes",
	"workflow",
	"data_import_column_header_map",
)

wildcard_keys = (
	"document_cache::*",
	"table_columns::*",
	*doctype_map_keys,
)


def clear_user_cache(user=None):
	from nts.desk.notifications import clear_notifications

	# this will automatically reload the global cache
	# so it is important to clear this first
	clear_notifications(user)

	if user:
		nts.cache.hdel_names(user_cache_keys, user)
		nts.cache.delete_keys("user:" + user)
		clear_defaults_cache(user)
	else:
		nts.cache.delete_key(user_cache_keys)
		clear_defaults_cache()
		clear_global_cache()


def clear_domain_cache(user=None):
	domain_cache_keys = ("domain_restricted_doctypes", "domain_restricted_pages")
	nts.cache.delete_value(domain_cache_keys)


def clear_global_cache():
	from nts.website.utils import clear_website_cache

	clear_doctype_cache()
	clear_website_cache()
	nts.cache.delete_value(global_cache_keys + bench_cache_keys)
	nts.setup_module_map()


def clear_defaults_cache(user=None):
	if user:
		for key in [user, *common_default_keys]:
			nts.client_cache.delete_value(f"defaults::{key}")
	elif nts.flags.in_install != "nts":
		nts.client_cache.delete_keys("defaults::*")


def clear_doctype_cache(doctype=None):
	clear_controller_cache(doctype)
	nts.client_cache.erase_persistent_caches(doctype=doctype)

	_clear_doctype_cache_from_redis(doctype)
	if hasattr(nts.db, "after_commit"):
		nts.db.after_commit.add(lambda: _clear_doctype_cache_from_redis(doctype))
		nts.db.after_rollback.add(lambda: _clear_doctype_cache_from_redis(doctype))


def _clear_doctype_cache_from_redis(doctype: str | None = None):
	from nts.desk.notifications import delete_notification_count_for
	from nts.email.doctype.notification.notification import clear_notification_cache
	from nts.model.meta import clear_meta_cache

	to_del = ["is_table", "doctype_modules"]

	if doctype:

		def clear_single(dt):
			nts.clear_document_cache(dt)
			# Wild card for all keys containing this doctype.
			# this can be excessive but this function isn't called often... ideally.
			nts.client_cache.delete_keys(f"*{dt}*")
			nts.cache.hdel_names(doctype_cache_keys, dt)
			clear_meta_cache(dt)

		clear_single(doctype)

		# clear all parent doctypes
		try:
			for dt in nts.get_all(
				"DocField",
				"parent",
				dict(fieldtype=["in", nts.model.table_fields], options=doctype),
				ignore_ddl=True,
			):
				clear_single(dt.parent)

			# clear all parent doctypes
			if not nts.flags.in_install:
				for dt in nts.get_all(
					"Custom Field",
					"dt",
					dict(fieldtype=["in", nts.model.table_fields], options=doctype),
					ignore_ddl=True,
				):
					clear_single(dt.dt)
		except nts.DoesNotExistError:
			pass  # core doctypes getting migrated.

		# clear all notifications
		delete_notification_count_for(doctype)

	else:
		# clear all
		to_del += doctype_cache_keys
		for pattern in wildcard_keys:
			to_del += nts.cache.get_keys(pattern)
		clear_meta_cache()

	clear_notification_cache()
	nts.cache.delete_value(to_del)


def clear_controller_cache(doctype=None, *, site=None):
	if not doctype:
		nts.controllers.pop(site or nts.local.site, None)
		nts.lazy_controllers.pop(site or nts.local.site, None)
		return

	if site_controllers := nts.controllers.get(site or nts.local.site):
		site_controllers.pop(doctype, None)

	if lazy_site_controllers := nts.lazy_controllers.get(site or nts.local.site):
		lazy_site_controllers.pop(doctype, None)


def get_doctype_map(doctype, name, filters=None, order_by=None):
	return nts.client_cache.get_value(
		get_doctype_map_key(doctype, name),
		generator=lambda: nts.get_all(doctype, filters=filters, order_by=order_by, ignore_ddl=True),
	)


def clear_doctype_map(doctype, name="*"):
	nts.client_cache.delete_keys(get_doctype_map_key(doctype, name))


def build_table_count_cache():
	if (
		nts.flags.in_patch
		or nts.flags.in_install
		or nts.flags.in_migrate
		or nts.flags.in_import
		or nts.flags.in_setup_wizard
	):
		return

	if nts.db.db_type != "sqlite":
		table_name = nts.qb.Field("table_name").as_("name")
		table_rows = nts.qb.Field("table_rows").as_("count")
		information_schema = nts.qb.Schema("information_schema")

		data = (nts.qb.from_(information_schema.tables).select(table_name, table_rows)).run(as_dict=True)
		counts = {d.get("name").replace("tab", "", 1): d.get("count", None) for d in data}
		nts.cache.set_value("information_schema:counts", counts)
	else:
		counts = {}
		name = nts.qb.Field("name")
		type = nts.qb.Field("type")
		sqlite_master = nts.qb.Schema("sqlite_master")
		data = nts.qb.from_(sqlite_master).select(name).where(type == "table").run(as_dict=True)
		for table in data:
			count = nts.db.sql(f"SELECT COUNT(*) FROM `{table.name}`")[0][0]
			counts[table.name.replace("tab", "", 1)] = count
		nts.cache.set_value("information_schema:counts", counts)

	return counts


def build_domain_restricted_doctype_cache(*args, **kwargs):
	if (
		nts.flags.in_patch
		or nts.flags.in_install
		or nts.flags.in_migrate
		or nts.flags.in_import
		or nts.flags.in_setup_wizard
	):
		return
	active_domains = nts.get_active_domains()
	doctypes = nts.get_all("DocType", filters={"restrict_to_domain": ("IN", active_domains)})
	doctypes = [doc.name for doc in doctypes]
	nts.cache.set_value("domain_restricted_doctypes", doctypes)

	return doctypes


def build_domain_restricted_page_cache(*args, **kwargs):
	if (
		nts.flags.in_patch
		or nts.flags.in_install
		or nts.flags.in_migrate
		or nts.flags.in_import
		or nts.flags.in_setup_wizard
	):
		return
	active_domains = nts.get_active_domains()
	pages = nts.get_all("Page", filters={"restrict_to_domain": ("IN", active_domains)})
	pages = [page.name for page in pages]
	nts.cache.set_value("domain_restricted_pages", pages)

	return pages


def clear_cache(user: str | None = None, doctype: str | None = None):
	"""Clear **User**, **DocType** or global cache.

	:param user: If user is given, only user cache is cleared.
	:param doctype: If doctype is given, only DocType cache is cleared."""
	import nts.cache_manager
	import nts.utils.caching
	from nts.website.router import clear_routing_cache

	if doctype:
		nts.cache_manager.clear_doctype_cache(doctype)
		reset_metadata_version()
	elif user:
		nts.cache_manager.clear_user_cache(user)
	else:  # everything
		# Delete ALL keys associated with this site.
		keys_to_delete = set(nts.cache.get_keys(""))
		for key in nts.get_hooks("persistent_cache_keys"):
			keys_to_delete.difference_update(nts.cache.get_keys(key))
		nts.cache.delete_value(list(keys_to_delete), make_keys=False)

		reset_metadata_version()
		nts.local.cache = {}
		nts.local.new_doc_templates = {}

		for fn in nts.get_hooks("clear_cache"):
			nts.get_attr(fn)()

	if (not doctype and not user) or doctype == "DocType":
		nts.utils.caching._SITE_CACHE.clear()
		nts.client_cache.clear_cache()

	nts.local.role_permissions = {}
	if hasattr(nts.local, "request_cache"):
		nts.local.request_cache.clear()
	if hasattr(nts.local, "system_settings"):
		del nts.local.system_settings
	if hasattr(nts.local, "website_settings"):
		del nts.local.website_settings

	clear_routing_cache()


def reset_metadata_version():
	"""Reset `metadata_version` (Client (Javascript) build ID) hash."""
	v = nts.generate_hash()
	nts.client_cache.set_value("metadata_version", v)
	return v
