# Copyright (c) 2015, nts Technologies Pvt. Ltd. and Contributors
# License: MIT. See LICENSE

import nts
from nts import _
from nts.query_builder import Field, functions


@nts.whitelist()
def get_all_nodes(doctype, label, parent, tree_method, **filters):
	"""Recursively gets all data from tree nodes"""

	filters.pop("cmd", None)
	filters.pop("data", None)

	tree_method = nts.get_attr(tree_method)

	nts.is_whitelisted(tree_method)

	data = tree_method(doctype, parent, **filters)
	out = [dict(parent=label, data=data)]

	filters.pop("is_root", None)
	to_check = [d.get("value") for d in data if d.get("expandable")]

	while to_check:
		parent = to_check.pop()
		data = tree_method(doctype, parent, is_root=False, **filters)
		out.append(dict(parent=parent, data=data))
		for d in data:
			if d.get("expandable"):
				to_check.append(d.get("value"))

	return out


@nts.whitelist()
def get_children(doctype, parent="", include_disabled=False, **filters):
	if isinstance(include_disabled, str):
		include_disabled = nts.sbool(include_disabled)
	return _get_children(doctype, parent, include_disabled=include_disabled)


def _get_children(doctype, parent="", ignore_permissions=False, include_disabled=False):
	parent_field = "parent_" + nts.scrub(doctype)
	meta = nts.get_meta(doctype)

	qb = (
		nts.qb.from_(doctype)
		.select(
			Field("name").as_("value"),
			Field(meta.get("title_field") or "name").as_("title"),
			Field("is_group").as_("expandable"),
		)
		.where(functions.IfNull(Field(parent_field), "").eq(parent))
		.where(Field("docstatus") < 2)
	)

	if nts.db.has_column(doctype, "disabled") and not include_disabled:
		# used 0 instead of `false` since type of check in postgres is smallint
		qb = qb.where(Field("disabled").eq(0))
	# Order by name and execute
	return qb.orderby("name").run(as_dict=True)


@nts.whitelist()
def add_node():
	args = make_tree_args(**nts.form_dict)
	doc = nts.get_doc(args)

	doc.save()


def make_tree_args(**kwarg):
	kwarg.pop("cmd", None)

	doctype = kwarg["doctype"]
	parent_field = "parent_" + nts.scrub(doctype)

	if kwarg["is_root"] == "false":
		kwarg["is_root"] = False
	if kwarg["is_root"] == "true":
		kwarg["is_root"] = True

	parent = kwarg.get("parent") or kwarg.get(parent_field)
	if doctype != parent:
		kwarg.update({parent_field: parent})

	return nts._dict(kwarg)
