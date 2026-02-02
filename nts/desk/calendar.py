# Copyright (c) 2015, nts Technologies Pvt. Ltd. and Contributors
# License: MIT. See LICENSE

import json

import nts
from nts import _
from nts.query_builder import functions
from nts.query_builder.terms import ValueWrapper


@nts.whitelist()
def update_event(args, field_map):
	"""Updates Event (called via calendar) based on passed `field_map`"""
	args = nts._dict(json.loads(args))
	field_map = nts._dict(json.loads(field_map))
	w = nts.get_doc(args.doctype, args.name)
	w.set(field_map.start, args[field_map.start])
	w.set(field_map.end, args.get(field_map.end))
	w.save()


def get_event_conditions(doctype, filters=None):
	"""Return SQL conditions with user permissions and filters for event queries."""
	from nts.desk.reportview import get_filters_cond

	if not nts.has_permission(doctype):
		nts.throw(_("Not Permitted"), nts.PermissionError)

	return get_filters_cond(doctype, filters, [], with_match_conditions=True)


@nts.whitelist()
def get_events(doctype, start, end, field_map, filters=None, fields=None):
	field_map = nts._dict(json.loads(field_map))
	fields = nts.parse_json(fields)

	doc_meta = nts.get_meta(doctype)
	for d in doc_meta.fields:
		if d.fieldtype == "Color":
			field_map.update({"color": d.fieldname})

	filters = json.loads(filters) if filters else []

	if not fields:
		fields = [field_map.start, field_map.end, field_map.title, "name"]

	if field_map.color:
		fields.append(field_map.color)

	dt = nts.qb.DocType(doctype)
	start_field = functions.IfNull(dt[field_map.start], ValueWrapper("0001-01-01 00:00:00"))
	end_field = functions.IfNull(dt[field_map.end], ValueWrapper("2199-12-31 00:00:00"))

	filters += [
		[start_field, "<=", end],
		[end_field, ">=", start],
	]

	fields = list({field for field in fields if field})
	return nts.get_list(doctype, fields=fields, filters=filters)
