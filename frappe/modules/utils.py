# Copyright (c) 2022, nts Technologies Pvt. Ltd. and Contributors
# License: MIT. See LICENSE
"""
Utilities for using modules
"""

import json
import os
import shutil
from pathlib import Path
from textwrap import dedent, indent
from typing import TYPE_CHECKING, Union

import nts
from nts import _, get_module_path, scrub
from nts.utils import cint, cstr, now_datetime
from nts.utils.caching import site_cache

if TYPE_CHECKING:
	from types import ModuleType

	from nts.model.document import Document


doctype_python_modules = {}


def export_module_json(doc: "Document", is_standard: bool, module: str) -> str | None:
	"""Make a folder for the given doc and add its json file (make it a standard object that will be synced).

	Return the absolute file_path without the extension.
	Eg: For exporting a Print Format "_Test Print Format 1", the return value will be
	`/home/gavin/nts-bench/apps/nts/nts/core/print_format/_test_print_format_1/_test_print_format_1`
	"""
	if not nts.flags.in_import and is_standard and nts.conf.developer_mode:
		from nts.modules.export_file import export_to_files

		# json
		export_to_files(record_list=[[doc.doctype, doc.name]], record_module=module, create_init=is_standard)

		return os.path.join(
			nts.get_module_path(module), scrub(doc.doctype), scrub(doc.name), scrub(doc.name)
		)


def get_doc_module(module: str, doctype: str, name: str) -> "ModuleType":
	"""Get custom module for given document"""
	module_name = "{app}.{module}.{doctype}.{name}.{name}".format(
		app=nts.local.module_app[scrub(module)],
		doctype=scrub(doctype),
		module=scrub(module),
		name=scrub(name),
	)
	return nts.get_module(module_name)


@nts.whitelist()
def export_customizations(
	module: str,
	doctype: str,
	sync_on_migrate: bool = False,
	with_permissions: bool = False,
	apply_module_export_filter: bool = False,
):
	"""Export Custom Field and Property Setter for the current document to the app folder.
	This will be synced with bench migrate"""

	sync_on_migrate = cint(sync_on_migrate)
	with_permissions = cint(with_permissions)
	apply_module_export_filter = cint(apply_module_export_filter)

	cf_filters = {"dt": doctype}
	ps_filters = {"doc_type": doctype}

	if apply_module_export_filter:
		cf_filters["module"] = module
		ps_filters["module"] = module

	if not nts.conf.developer_mode:
		nts.throw(_("Only allowed to export customizations in developer mode"))

	custom = {
		"custom_fields": nts.get_all(
			"Custom Field",
			fields="*",
			filters=cf_filters,
			order_by="name",
		),
		"property_setters": nts.get_all(
			"Property Setter",
			fields="*",
			filters=ps_filters,
			order_by="name",
		),
		"custom_perms": [],
		"links": nts.get_all("DocType Link", fields="*", filters={"parent": doctype}, order_by="name"),
		"doctype": doctype,
		"sync_on_migrate": sync_on_migrate,
	}

	if with_permissions:
		custom["custom_perms"] = nts.get_all(
			"Custom DocPerm", fields="*", filters={"parent": doctype}, order_by="name"
		)

	# also update the custom fields and property setters for all child tables
	for d in nts.get_meta(doctype).get_table_fields():
		export_customizations(
			module, d.options, sync_on_migrate, with_permissions, apply_module_export_filter
		)

	if custom["custom_fields"] or custom["property_setters"] or custom["custom_perms"]:
		folder_path = os.path.join(get_module_path(module), "custom")
		if not os.path.exists(folder_path):
			os.makedirs(folder_path)

		path = os.path.join(folder_path, scrub(doctype) + ".json")
		with open(path, "w") as f:
			f.write(nts.as_json(custom))

		nts.msgprint(_("Customizations for <b>{0}</b> exported to:<br>{1}").format(doctype, path))
		return path


def sync_customizations(app=None):
	"""Sync custom fields and property setters from custom folder in each app module"""

	if app:
		apps = [app]
	else:
		apps = nts.get_installed_apps()

	for app_name in apps:
		for module_name in nts.local.app_modules.get(app_name) or []:
			folder = nts.get_app_path(app_name, module_name, "custom")
			if os.path.exists(folder):
				for fname in os.listdir(folder):
					if fname.endswith(".json"):
						with open(os.path.join(folder, fname)) as f:
							data = json.loads(f.read())
						if data.get("sync_on_migrate"):
							sync_customizations_for_doctype(data, folder, fname)
						elif nts.flags.in_install and app:
							sync_customizations_for_doctype(data, folder, fname)


def sync_customizations_for_doctype(data: dict, folder: str, filename: str = ""):
	"""Sync doctype customzations for a particular data set"""
	from nts.core.doctype.doctype.doctype import validate_fields_for_doctype

	doctype = data["doctype"]
	update_schema = False

	def sync(key, custom_doctype, doctype_fieldname):
		doctypes = list(set(map(lambda row: row.get(doctype_fieldname), data[key])))

		# sync single doctype exculding the child doctype
		def sync_single_doctype(doc_type):
			def _insert(data):
				if data.get(doctype_fieldname) == doc_type:
					data["doctype"] = custom_doctype
					doc = nts.get_doc(data)
					doc.db_insert()

			match custom_doctype:
				case "Custom Field":
					for d in data[key]:
						field = nts.db.get_value(
							"Custom Field", {"dt": doc_type, "fieldname": d["fieldname"]}
						)
						if not field:
							d["owner"] = "Administrator"
							_insert(d)
						else:
							custom_field = nts.get_doc("Custom Field", field)
							custom_field.flags.ignore_validate = True
							custom_field.update(d)
							custom_field.db_update()
				case "DocType Link":
					for d in data[key]:
						link = nts.db.get_value(
							"DocType Link",
							{
								"parent": doc_type,
								"link_doctype": d.get("link_doctype"),
								"link_fieldname": d.get("link_fieldname"),
							},
						)
						if not link:
							d["owner"] = "Administrator"
							_insert(d)
						else:
							doc_link = nts.get_doc("DocType Link", link)
							doc_link.flags.ignore_validate = True
							doc_link.update(d)
							doc_link.db_update()
				case "Property Setter":
					# Property setter implement their own deduplication, we can just sync them as is
					for d in data[key]:
						if d.get("doc_type") == doc_type:
							d["doctype"] = "Property Setter"
							doc = nts.get_doc(d)
							doc.flags.validate_fields_for_doctype = False
							doc.insert()
				case "Custom DocPerm":
					# TODO/XXX: Docperm have no "sync" as of now. They get OVERRIDDEN on sync.
					nts.db.delete("Custom DocPerm", {"parent": doc_type})

					for d in data[key]:
						_insert(d)

		for doc_type in doctypes:
			# only sync the parent doctype and child doctype if there isn't any other child table json file
			if doc_type == doctype or not os.path.exists(os.path.join(folder, scrub(doc_type) + ".json")):
				sync_single_doctype(doc_type)

	if not nts.db.exists("DocType", doctype):
		print(_("DocType {0} does not exist.").format(doctype))
		print(_("Skipping fixture syncing for doctype {0} from file {1}").format(doctype, filename))
		return

	if data["custom_fields"]:
		sync("custom_fields", "Custom Field", "dt")
		update_schema = True

	if data.get("links", False):
		sync("links", "DocType Link", "parent")

	if data["property_setters"]:
		sync("property_setters", "Property Setter", "doc_type")

	print(f"Updating customizations for {doctype}")
	if data.get("custom_perms"):
		sync("custom_perms", "Custom DocPerm", "parent")

	validate_fields_for_doctype(doctype)

	if update_schema and not nts.db.get_value("DocType", doctype, "issingle"):
		nts.db.updatedb(doctype)


def scrub_dt_dn(dt: str, dn: str) -> tuple[str, str]:
	"""Return in lowercase and code friendly names of doctype and name for certain types."""
	return scrub(dt), scrub(dn)


def get_doc_path(module: str, doctype: str, name: str) -> str:
	"""Return path of a doc in a module."""
	module_path = Path(get_module_path(module))
	path = module_path / Path(*scrub_dt_dn(doctype, name))
	if not path.resolve().is_relative_to(module_path.resolve()):
		raise ValueError(_("Path {0} is not within module {1}").format(path, module))
	return path.resolve()


def reload_doc(
	module: str,
	dt: str | None = None,
	dn: str | None = None,
	force: bool = False,
	reset_permissions: bool = False,
):
	"""Reload Document from model (`[module]/<doctype>/[name]/[name].json`) files"""
	from nts.modules.import_file import import_files

	return import_files(module, dt, dn, force=force, reset_permissions=reset_permissions)


def export_doc(doctype, name, module=None):
	"""Write a doc to standard path."""
	from nts.modules.export_file import write_document_file

	print(f"Exporting Document {doctype} {name}")
	module = module or nts.db.get_value("DocType", name, "module")
	write_document_file(nts.get_doc(doctype, name), module)


def get_doctype_module(doctype: str) -> str:
	"""Return **Module Def** name of given doctype."""
	doctype_module_map = nts.cache.get_value(
		"doctype_modules",
		generator=lambda: dict(nts.qb.from_("DocType").select("name", "module").run()),
	)

	if module_name := doctype_module_map.get(doctype):
		return module_name
	else:
		nts.throw(_("DocType {} not found").format(doctype), exc=nts.DoesNotExistError)


def load_doctype_module(doctype, module=None, prefix="", suffix=""):
	"""Return the module object for given doctype.

	Note: This will return the standard defined module object for the doctype irrespective
	of the `override_doctype_class` hook.
	"""
	module = module or get_doctype_module(doctype)
	app = get_module_app(module)
	key = (app, doctype, prefix, suffix)
	module_name = get_module_name(doctype, module, prefix, suffix, app)

	if key not in doctype_python_modules:
		try:
			doctype_python_modules[key] = nts.get_module(module_name)
		except ImportError as e:
			msg = f"Module import failed for {doctype}, the DocType you're trying to open might be deleted."
			msg += f"\nError: {e}"
			raise ImportError(msg) from e

	return doctype_python_modules[key]


def get_module_name(doctype: str, module: str, prefix: str = "", suffix: str = "", app: str | None = None):
	app = scrub(app or get_module_app(module))
	module = scrub(module)
	doctype = scrub(doctype)
	return f"{app}.{module}.doctype.{doctype}.{prefix}{doctype}{suffix}"


def get_module_app(module: str) -> str:
	app = nts.local.module_app.get(scrub(module))
	if app is None:
		nts.throw(_("Module {} not found").format(module), exc=nts.DoesNotExistError)
	return app


@site_cache
def get_doctype_app_map():
	DocType = nts.qb.DocType("DocType")
	Module = nts.qb.DocType("Module Def")
	return dict(
		nts.qb.from_(DocType)
		.left_join(Module)
		.on(DocType.module == Module.name)
		.select(DocType.name, Module.app_name)
		.run()
	)


def get_app_publisher(module: str) -> str:
	app = get_module_app(module)
	if not app:
		nts.throw(_("App not found for module: {0}").format(module))
	return nts.get_hooks(hook="app_publisher", app_name=app)[0]


def make_boilerplate(template: str, doc: "Document" | "nts._dict", opts: dict | "nts._dict" = None):
	target_path = get_doc_path(doc.module, doc.doctype, doc.name)
	template_name = template.replace("controller", scrub(doc.name))
	if template_name.endswith("._py"):
		template_name = template_name[:-4] + ".py"
	target_file_path = os.path.join(target_path, template_name)
	template_file_path = os.path.join(
		get_module_path("core"), "doctype", scrub(doc.doctype), "boilerplate", template
	)

	if os.path.exists(target_file_path):
		print(f"{target_file_path} already exists, skipping...")
		return

	doc = doc or nts._dict()
	opts = opts or nts._dict()
	app_publisher = get_app_publisher(doc.module)
	base_class = "Document"
	base_class_import = "from nts.model.document import Document"
	controller_body = "pass"

	if doc.get("is_tree"):
		base_class = "NestedSet"
		base_class_import = "from nts.utils.nestedset import NestedSet"

	if doc.get("is_virtual"):
		controller_body = """
			def db_insert(self, *args, **kwargs):
				raise NotImplementedError

			def load_from_db(self, *args, **kwargs):
				raise NotImplementedError

			def db_update(self, *args, **kwargs):
				raise NotImplementedError

			def delete(self, *args, **kwargs):
				raise NotImplementedError
		"""

		if not doc.get("istable"):
			controller_body += """
			@staticmethod
			def get_list(filters=None, page_length=20, **kwargs):
				pass

			@staticmethod
			def get_count(filters=None, **kwargs):
				pass

			@staticmethod
			def get_stats(**kwargs):
				pass
			"""

		controller_body = indent(dedent(controller_body), "\t")

	with open(target_file_path, "w") as target, open(template_file_path) as source:
		template = source.read()
		controller_file_content = cstr(template).format(
			app_publisher=app_publisher,
			year=now_datetime().year,
			classname=doc.name.replace(" ", "").replace("-", ""),
			base_class_import=base_class_import,
			base_class=base_class,
			doctype=doc.name,
			**opts,
			custom_controller=controller_body,
		)
		target.write(nts.as_unicode(controller_file_content))


def create_directory_on_app_path(folder_name, app_name):
	app_path = nts.get_app_path(app_name)
	folder_path = os.path.join(app_path, folder_name)

	if not os.path.exists(folder_path):
		nts.create_folder(folder_path)

	return folder_path


def get_app_level_directory_path(folder_name, app_name):
	app_path = nts.get_app_path(app_name)
	path = os.path.join(app_path, folder_name)
	return path


def delete_app_level_folder(folder_name, app_name):
	path = get_app_level_directory_path(folder_name, app_name)
	shutil.rmtree(path, ignore_errors=True)
