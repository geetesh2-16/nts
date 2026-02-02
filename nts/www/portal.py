import json

import nts
from nts import _, cint
from nts.model.document import Document
from nts.utils.data import quoted
from nts.www.list import get_list_context, get_list_data


def get_context(context, **dict_params):
	if nts.session.user == "Guest":
		raise nts.PermissionError
	nts.local.form_dict.update(dict_params)
	context.show_sidebar = True
	doctype = nts.local.form_dict.doctype
	if doctype:
		context.meta = nts.get_meta(doctype)
		context.update(get_list_context(context, doctype) or {})
		context.update(get(**nts.local.form_dict))
		context.home_page = "/portal"
		context.doctype = nts.local.form_dict.doctype
	return context


def set_route(context):
	"""Set link for the list item"""
	if context.web_form_name:
		context.route = f"{context.pathname}?name={quoted(context.doc.name)}"
	elif context.doc and getattr(context.doc, "route", None):
		context.route = context.doc.route
	else:
		context.route = f"{context.pathname or quoted(context.doc.doctype)}/{quoted(context.doc.name)}"


def get(
	doctype: str,
	txt: str | None = None,
	limit_start: int = 0,
	limit: int = 20,
	pathname: str | None = None,
	**kwargs,
):
	"""Return processed HTML page for a standard listing."""
	limit_start = cint(limit_start)
	raw_result = get_list_data(doctype, txt, limit_start, limit=limit + 1, **kwargs)
	show_more = len(raw_result) > limit
	if show_more:
		raw_result = raw_result[:-1]

	meta = nts.get_meta(doctype)
	list_context = nts.flags.list_context

	if not raw_result:
		return {"result": []}

	if txt:
		list_context.default_subtitle = _('Filtered by "{0}"').format(txt)

	result = []
	row_template = list_context.row_template or "templates/includes/list/row_template.html"
	list_view_fields = [df for df in meta.fields if df.in_list_view][:4]

	for doc in raw_result:
		doc.doctype = doctype
		new_context = nts._dict(doc=doc, meta=meta, list_view_fields=list_view_fields)

		if not list_context.get_list and not isinstance(new_context.doc, Document):
			new_context.doc = nts.get_doc(doc.doctype, doc.name)
			new_context.update(new_context.doc.as_dict())

		if not nts.in_test:
			pathname = pathname or nts.local.request.path
			new_context["pathname"] = pathname.strip("/ ")
		new_context.update(list_context)
		set_route(new_context)
		rendered_row = nts.render_template(row_template, new_context, is_path=True)
		result.append(rendered_row)

	from nts.utils.response import json_handler

	return {
		"raw_result": json.dumps(raw_result, default=json_handler),
		"result": result,
		"show_more": show_more,
		"next_start": limit_start + limit,
	}
