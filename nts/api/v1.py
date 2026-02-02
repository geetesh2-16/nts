import json

from werkzeug.routing import Rule

import nts
from nts import _
from nts.utils import attach_expanded_links
from nts.utils.data import sbool


def document_list(doctype: str):
	if nts.form_dict.get("fields"):
		nts.form_dict["fields"] = json.loads(nts.form_dict["fields"])

	if nts.form_dict.get("expand"):
		nts.form_dict["expand"] = json.loads(nts.form_dict["expand"])

	# set limit of records for nts.get_list
	nts.form_dict.setdefault(
		"limit_page_length",
		nts.form_dict.limit or nts.form_dict.limit_page_length or 20,
	)

	# convert strings to native types - only as_dict and debug accept bool
	for param in ["as_dict", "debug"]:
		param_val = nts.form_dict.get(param)
		if param_val is not None:
			nts.form_dict[param] = sbool(param_val)

	# evaluate nts.get_list
	return nts.call(nts.client.get_list, doctype, **nts.form_dict)


def handle_rpc_call(method: str):
	import nts.handler

	method = method.split("/")[0]  # for backward compatiblity

	nts.form_dict.cmd = method
	return nts.handler.handle()


def create_doc(doctype: str):
	data = get_request_form_data()
	data.pop("doctype", None)
	return nts.new_doc(doctype, **data).insert()


def update_doc(doctype: str, name: str):
	data = get_request_form_data()

	doc = nts.get_doc(doctype, name, for_update=True)
	if "flags" in data:
		del data["flags"]

	doc.update(data)
	doc.save()

	# check for child table doctype
	if doc.get("parenttype"):
		nts.get_doc(doc.parenttype, doc.parent).save()

	return doc


def delete_doc(doctype: str, name: str):
	# TODO: child doc handling
	nts.delete_doc(doctype, name, ignore_missing=False)
	nts.response.http_status_code = 202
	return "ok"


def read_doc(doctype: str, name: str):
	# Backward compatiblity
	if "run_method" in nts.form_dict:
		return execute_doc_method(doctype, name)

	doc = nts.get_doc(doctype, name)
	doc.check_permission("read")
	doc.apply_fieldlevel_read_permissions()
	if sbool(nts.form_dict.get("expand_links")):
		doc_dict = doc.as_dict()
		get_values_for_link_and_dynamic_link_fields(doc_dict)
		get_values_for_table_and_multiselect_fields(doc_dict)
		return doc_dict

	return doc


def get_values_for_link_and_dynamic_link_fields(doc_dict):
	meta = nts.get_meta(doc_dict.doctype)
	link_fields = meta.get_link_fields() + meta.get_dynamic_link_fields()

	for field in link_fields:
		if not (doc_fieldvalue := getattr(doc_dict, field.fieldname, None)):
			continue

		doctype = field.options if field.fieldtype == "Link" else doc_dict.get(field.options)

		link_doc = nts.get_doc(doctype, doc_fieldvalue)
		doc_dict.update({field.fieldname: link_doc})


def get_values_for_table_and_multiselect_fields(doc_dict):
	meta = nts.get_meta(doc_dict.doctype)
	table_fields = meta.get_table_fields()

	for field in table_fields:
		table_link_fieldnames = [f.fieldname for f in nts.get_meta(field.options).get_link_fields()]
		attach_expanded_links(field.options, doc_dict.get(field.fieldname), table_link_fieldnames)


def execute_doc_method(doctype: str, name: str, method: str | None = None):
	method = method or nts.form_dict.pop("run_method")
	doc = nts.get_doc(doctype, name)
	doc.is_whitelisted(method)

	if nts.request.method == "GET":
		doc.check_permission("read")
		return doc.run_method(method, **nts.form_dict)

	elif nts.request.method == "POST":
		doc.check_permission("write")
		return doc.run_method(method, **nts.form_dict)


def get_request_form_data():
	if nts.form_dict.data is None:
		data = nts.safe_decode(nts.request.get_data())
	else:
		data = nts.form_dict.data

	try:
		return nts.parse_json(data)
	except ValueError:
		return nts.form_dict


url_rules = [
	Rule("/method/<path:method>", endpoint=handle_rpc_call),
	Rule("/resource/<doctype>", methods=["GET"], endpoint=document_list),
	Rule("/resource/<doctype>", methods=["POST"], endpoint=create_doc),
	Rule("/resource/<doctype>/<path:name>/", methods=["GET"], endpoint=read_doc),
	Rule("/resource/<doctype>/<path:name>/", methods=["PUT"], endpoint=update_doc),
	Rule("/resource/<doctype>/<path:name>/", methods=["DELETE"], endpoint=delete_doc),
	Rule("/resource/<doctype>/<path:name>/", methods=["POST"], endpoint=execute_doc_method),
]
