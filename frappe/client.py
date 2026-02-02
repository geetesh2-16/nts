# Copyright (c) 2015, nts Technologies Pvt. Ltd. and Contributors
# License: MIT. See LICENSE
import json
import os
from typing import TYPE_CHECKING

import nts
import nts.model
import nts.utils
from nts import _
from nts.desk.reportview import validate_args
from nts.desk.search import PAGE_LENGTH_FOR_LINK_VALIDATION, search_widget
from nts.utils import attach_expanded_links, get_safe_filters
from nts.utils.caching import http_cache

if TYPE_CHECKING:
	from nts.model.document import Document

"""
Handle RESTful requests that are mapped to the `/api/resource` route.

Requests via ntsClient are also handled here.
"""


@nts.whitelist()
def get_list(
	doctype,
	fields=None,
	filters=None,
	group_by=None,
	order_by=None,
	limit_start=None,
	limit_page_length=20,
	parent=None,
	debug: bool = False,
	as_dict: bool = True,
	or_filters=None,
	expand=None,
):
	"""Return a list of records by filters, fields, ordering and limit.

	:param doctype: DocType of the data to be queried
	:param fields: fields to be returned. Default is `name`
	:param filters: filter list by this dict
	:param order_by: Order by this fieldname
	:param limit_start: Start at this index
	:param limit_page_length: Number of records to be returned (default 20)"""

	args = nts._dict(
		doctype=doctype,
		parent_doctype=parent,
		fields=fields,
		filters=filters,
		or_filters=or_filters,
		group_by=group_by,
		order_by=order_by,
		limit_start=limit_start,
		limit_page_length=limit_page_length,
		debug=debug,
		as_list=not as_dict,
	)

	validate_args(args)
	_list = nts.get_list(**args)

	if not expand:
		return _list

	if fields and not fields[0] == "*":
		expand = [f for f in expand if f in fields]

	attach_expanded_links(doctype, _list, expand)

	return _list


@nts.whitelist()
def get_count(doctype, filters=None, debug=False, cache=False):
	from nts.desk.reportview import get_count

	nts.form_dict.doctype = doctype
	nts.form_dict.filters = get_safe_filters(filters)
	nts.form_dict.debug = debug

	return get_count()


@nts.whitelist()
def get(doctype, name=None, filters=None, parent=None):
	"""Return a document by name or filters.

	:param doctype: DocType of the document to be returned
	:param name: return document of this `name`
	:param filters: If name is not set, filter by these values and return the first match"""

	if name:
		doc = nts.get_doc(doctype, name)
	elif filters or filters == {}:
		doc = nts.get_doc(doctype, nts.parse_json(filters))
	else:
		doc = nts.get_doc(doctype)  # single

	doc.check_permission()
	doc.apply_fieldlevel_read_permissions()

	return doc.as_dict()


@nts.whitelist()
def get_value(doctype, fieldname, filters=None, as_dict=True, debug=False, parent=None):
	"""Return a value from a document.

	:param doctype: DocType to be queried
	:param fieldname: Field to be returned (default `name`)
	:param filters: dict or string for identifying the record"""

	if not nts.has_permission(doctype, parent_doctype=parent):
		nts.throw(_("No permission for {0}").format(_(doctype)), nts.PermissionError)

	filters = get_safe_filters(filters)
	if isinstance(filters, str):
		filters = {"name": filters}

	try:
		fields = nts.parse_json(fieldname)
	except (TypeError, ValueError):
		# name passed, not json
		fields = [fieldname]

	# check whether the used filters were really parseable and usable
	# and did not just result in an empty string or dict
	if not filters:
		filters = None

	if nts.get_meta(doctype).issingle:
		value = nts.db.get_values_from_single(fields, filters, doctype, as_dict=as_dict, debug=debug)
	else:
		value = get_list(
			doctype,
			filters=filters,
			fields=fields,
			debug=debug,
			limit_page_length=1,
			parent=parent,
			as_dict=as_dict,
		)

	if as_dict:
		return value[0] if value else {}

	if not value:
		return

	return value[0] if len(fields) > 1 else value[0][0]


@nts.whitelist()
def get_single_value(doctype, field):
	if not nts.has_permission(doctype):
		nts.throw(_("No permission for {0}").format(_(doctype)), nts.PermissionError)

	return nts.db.get_single_value(doctype, field)


@nts.whitelist(methods=["POST", "PUT"])
def set_value(doctype, name, fieldname, value=None):
	"""Set a value using get_doc, group of values

	:param doctype: DocType of the document
	:param name: name of the document
	:param fieldname: fieldname string or JSON / dict with key value pair
	:param value: value if fieldname is JSON / dict"""

	if fieldname in (nts.model.default_fields + nts.model.child_table_fields):
		nts.throw(_("Cannot edit standard fields"))

	if not value:
		values = fieldname
		if isinstance(fieldname, str):
			try:
				values = json.loads(fieldname)
			except ValueError:
				values = {fieldname: ""}
	else:
		values = {fieldname: value}

	# check for child table doctype
	if not nts.get_meta(doctype).istable:
		doc = nts.get_doc(doctype, name)
		doc.update(values)
	else:
		doc = nts.db.get_value(doctype, name, ["parenttype", "parent"], as_dict=True)
		doc = nts.get_doc(doc.parenttype, doc.parent)
		child = doc.getone({"doctype": doctype, "name": name})
		child.update(values)

	doc.save()

	return doc.as_dict()


@nts.whitelist(methods=["POST", "PUT"])
def insert(doc=None):
	"""Insert a document

	:param doc: JSON or dict object to be inserted"""
	if isinstance(doc, str):
		doc = json.loads(doc)

	return insert_doc(doc).as_dict()


@nts.whitelist(methods=["POST", "PUT"])
def insert_many(docs=None):
	"""Insert multiple documents

	:param docs: JSON or list of dict objects to be inserted in one request"""
	if isinstance(docs, str):
		docs = json.loads(docs)

	if len(docs) > 200:
		nts.throw(_("Only 200 inserts allowed in one request"))

	return [insert_doc(doc).name for doc in docs]


@nts.whitelist(methods=["POST", "PUT"])
def save(doc):
	"""Update (save) an existing document

	:param doc: JSON or dict object with the properties of the document to be updated"""
	if isinstance(doc, str):
		doc = json.loads(doc)

	doc = nts.get_doc(doc)
	doc.save()

	return doc.as_dict()


@nts.whitelist(methods=["POST", "PUT"])
def rename_doc(doctype, old_name, new_name, merge=False):
	"""Rename document

	:param doctype: DocType of the document to be renamed
	:param old_name: Current `name` of the document to be renamed
	:param new_name: New `name` to be set"""
	new_name = nts.rename_doc(doctype, old_name, new_name, merge=merge)
	return new_name


@nts.whitelist(methods=["POST", "PUT"])
def submit(doc):
	"""Submit a document

	:param doc: JSON or dict object to be submitted remotely"""
	if isinstance(doc, str):
		doc = json.loads(doc)

	doc = nts.get_doc(doc)
	doc.submit()

	return doc.as_dict()


@nts.whitelist(methods=["POST", "PUT"])
def cancel(doctype, name):
	"""Cancel a document

	:param doctype: DocType of the document to be cancelled
	:param name: name of the document to be cancelled"""
	wrapper = nts.get_doc(doctype, name)
	wrapper.cancel()

	return wrapper.as_dict()


@nts.whitelist(methods=["DELETE", "POST"])
def delete(doctype, name):
	"""Delete a remote document

	:param doctype: DocType of the document to be deleted
	:param name: name of the document to be deleted"""
	delete_doc(doctype, name)


@nts.whitelist(methods=["POST", "PUT"])
def bulk_update(docs):
	"""Bulk update documents

	:param docs: JSON list of documents to be updated remotely. Each document must have `docname` property"""
	docs = json.loads(docs)
	failed_docs = []
	for doc in docs:
		doc.pop("flags", None)
		try:
			existing_doc = nts.get_doc(doc["doctype"], doc["docname"])
			existing_doc.update(doc)
			existing_doc.save()
		except Exception:
			failed_docs.append({"doc": doc, "exc": nts.utils.get_traceback()})

	return {"failed_docs": failed_docs}


@nts.whitelist()
def has_permission(doctype: str, docname: str, perm_type: str = "read"):
	"""Return a JSON with data whether the document has the requested permission.

	:param doctype: DocType of the document to be checked
	:param docname: `name` of the document to be checked
	:param perm_type: one of `read`, `write`, `create`, `submit`, `cancel`, `report`. Default is `read`"""
	# perm_type can be one of read, write, create, submit, cancel, report
	return {"has_permission": nts.has_permission(doctype, perm_type.lower(), docname)}


@nts.whitelist()
def get_doc_permissions(doctype: str, docname: str):
	"""Return an evaluated document permissions dict like `{"read":1, "write":1}`.

	:param doctype: DocType of the document to be evaluated
	:param docname: `name` of the document to be evaluated
	"""
	doc = nts.get_lazy_doc(doctype, docname)
	return {"permissions": nts.permissions.get_doc_permissions(doc)}


@nts.whitelist()
def get_password(doctype: str, name: str, fieldname: str):
	"""Return a password type property. Only applicable for System Managers

	:param doctype: DocType of the document that holds the password
	:param name: `name` of the document that holds the password
	:param fieldname: `fieldname` of the password property
	"""
	nts.only_for("System Manager")
	return nts.get_lazy_doc(doctype, name).get_password(fieldname)


from nts.deprecation_dumpster import get_js as _get_js

get_js = nts.whitelist()(_get_js)


@nts.whitelist(allow_guest=True)
def get_time_zone():
	"""Return the default time zone."""
	return {"time_zone": nts.defaults.get_defaults().get("time_zone")}


@nts.whitelist(methods=["POST", "PUT"])
def attach_file(
	filename=None,
	filedata=None,
	doctype=None,
	docname=None,
	folder=None,
	decode_base64=False,
	is_private=None,
	docfield=None,
):
	"""Attach a file to Document

	:param filename: filename e.g. test-file.txt
	:param filedata: base64 encode filedata which must be urlencoded
	:param doctype: Reference DocType to attach file to
	:param docname: Reference DocName to attach file to
	:param folder: Folder to add File into
	:param decode_base64: decode filedata from base64 encode, default is False
	:param is_private: Attach file as private file (1 or 0)
	:param docfield: file to attach to (optional)"""

	doc = nts.get_lazy_doc(doctype, docname, check_permission=True)

	file = nts.get_doc(
		{
			"doctype": "File",
			"file_name": filename,
			"attached_to_doctype": doctype,
			"attached_to_name": docname,
			"attached_to_field": docfield,
			"folder": folder,
			"is_private": is_private,
			"content": filedata,
			"decode": decode_base64,
		}
	).save()

	if docfield and doctype:
		doc.set(docfield, file.file_url)
		doc.save()

	return file


@nts.whitelist()
@http_cache(max_age=10 * 60)
def is_document_amended(doctype: str, docname: str):
	if nts.permissions.has_permission(doctype):
		try:
			return nts.db.exists(doctype, {"amended_from": docname})
		except nts.db.InternalError:
			pass

	return False


@nts.whitelist(methods=["GET", "POST"])
def validate_link_and_fetch(
	doctype: str,
	docname: str,
	fields_to_fetch: list[str] | str | None = None,
	# search_widget parameters
	query: str | None = None,
	filters: dict | list | str | None = None,
	**search_args,
):
	if not docname:
		nts.throw(_("Document Name must not be empty"))

	meta = nts.get_meta(doctype)
	fields_to_fetch = nts.parse_json(fields_to_fetch)

	# only cache is no fields to fetch and request is GET
	can_cache = not fields_to_fetch and nts.request.method == "GET"

	# Use search_widget to validate - ensures filters/custom queries are respected
	# in addition to standard permission checks
	# we match the exact docname for non-custom queries and rely on txt for custom queries
	search_args.update(
		as_dict=False,
		# when relying on txt (custom queries), we want to match "A" with "A" only and not "A1", "BA" etc.
		# so we set page_length to a conservative value within which exact match is expected to appear
		page_length=PAGE_LENGTH_FOR_LINK_VALIDATION,
		# translated doctypes are expected to be searchable with translated values, even for custom queries
		# for non-custom queries, docname is always matched exactly so we don't translate it
		txt=_(docname) if (query and meta.translated_doctype) else docname,
		for_link_validation=True,
	)

	search_result = nts.call(
		search_widget,
		doctype=doctype,
		query=query,
		filters=filters,
		**search_args,
	)

	if not search_result:
		return {}  # does not exist or filtered out

	values = None
	is_virtual_dt = bool(meta.get("is_virtual"))
	if is_virtual_dt:
		try:
			doc = nts.get_doc(doctype, docname)
			doc.check_permission("select" if nts.only_has_select_perm(doctype) else "read")
			values = {"name": doc.name}

		except nts.DoesNotExistError:
			nts.clear_last_message()
	else:
		# get value in the right case and type (str | int)
		# for matching with search result
		columns_to_fetch = ["name"]
		if nts.is_table(doctype):
			columns_to_fetch.append("parenttype")  # for child table permission check
		values = nts.db.get_value(doctype, docname, columns_to_fetch, as_dict=True)

	if not values:
		return {}  # does not exist

	name_to_compare = values["name"]
	# this will be used to fetch fields later
	parent_doctype = values.pop("parenttype", None)

	# try to match name in search result
	# if search_result is large, assume valid link (result may not appear in some custom queries)
	if len(search_result) < PAGE_LENGTH_FOR_LINK_VALIDATION and not any(
		item[0] == name_to_compare for item in search_result
	):
		return {}  # no permission or filtered out

	# don't cache or fetch for virtual doctypes
	if is_virtual_dt:
		return values

	if not fields_to_fetch:
		if can_cache:
			nts.local.response_headers.set(
				"Cache-Control", "private,max-age=1800,stale-while-revalidate=7200"
			)
		return values

	try:
		values.update(get_value(doctype, fields_to_fetch, docname, parent=parent_doctype))
	except nts.PermissionError:
		nts.clear_last_message()
		nts.msgprint(
			_("You need {0} permission to fetch values from {1} {2}").format(
				nts.bold(_("Read")), nts.bold(doctype), nts.bold(docname)
			),
			title=_("Cannot Fetch Values"),
			indicator="orange",
		)

	return values


def insert_doc(doc) -> "Document":
	"""Insert document and return parent document object with appended child document if `doc` is child document else return the inserted document object.

	:param doc: doc to insert (dict)"""

	doc = nts._dict(doc)
	if nts.is_table(doc.doctype):
		if not (doc.parenttype and doc.parent and doc.parentfield):
			nts.throw(_("Parenttype, Parent and Parentfield are required to insert a child record"))

		# inserting a child record
		parent = nts.get_doc(doc.parenttype, doc.parent)
		parent.append(doc.parentfield, doc)
		parent.save()
		return parent

	return nts.get_doc(doc).insert()


def delete_doc(doctype, name):
	"""Deletes document
	if doctype is a child table, then deletes the child record using the parent doc
	so that the parent doc's `on_update` is called
	"""

	if nts.is_table(doctype):
		values = nts.db.get_value(doctype, name, ["parenttype", "parent", "parentfield"])
		if not values:
			raise nts.DoesNotExistError(doctype=doctype)

		parenttype, parent, parentfield = values
		parent = nts.get_doc(parenttype, parent)
		if not parent.has_permission("write"):
			raise nts.DoesNotExistError(doctype=doctype)

		for row in parent.get(parentfield):
			if row.name == name:
				parent.remove(row)
				parent.save()
				break
	else:
		nts.delete_doc(doctype, name, ignore_missing=False)
