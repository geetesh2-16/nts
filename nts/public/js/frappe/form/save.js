// Copyright (c) 2015, nts Technologies Pvt. Ltd. and Contributors
// MIT License. See license.txt

nts.ui.form.save = function (frm, action, callback, btn) {
	$(btn).prop("disabled", true);

	// specified here because there are keyboard shortcuts to save
	const working_label = {
		Save: __("Saving", null, "Freeze message while saving a document"),
		Submit: __("Submitting", null, "Freeze message while submitting a document"),
		Update: __("Updating", null, "Freeze message while updating a document"),
		Amend: __("Amending", null, "Freeze message while amending a document"),
		Cancel: __("Cancelling", null, "Freeze message while cancelling a document"),
	}[toTitle(action)];

	var freeze_message = working_label ? __(working_label) : "";

	var save = function () {
		$(frm.wrapper).addClass("validated-form");
		if ((action !== "Save" || frm.is_dirty()) && nts.ui.form.check_mandatory(frm)) {
			_call({
				method: "nts.desk.form.save.savedocs",
				args: { doc: frm.doc, action: action },
				callback: function (r) {
					$(document).trigger("save", [frm.doc]);
					callback(r);
				},
				error: function (r) {
					callback(r);
				},
				btn: btn,
				freeze_message: freeze_message,
			});
		} else {
			!frm.is_dirty() &&
				nts.show_alert({ message: __("No changes in document"), indicator: "orange" });
			$(btn).prop("disabled", false);
		}
	};

	var cancel = function () {
		var args = {
			doctype: frm.doc.doctype,
			name: frm.doc.name,
		};

		// update workflow state value if workflow exists
		var workflow_state_fieldname = nts.workflow.get_state_fieldname(frm.doctype);
		if (workflow_state_fieldname) {
			$.extend(args, {
				workflow_state_fieldname: workflow_state_fieldname,
				workflow_state: frm.doc[workflow_state_fieldname],
			});
		}

		_call({
			method: "nts.desk.form.save.cancel",
			args: args,
			callback: function (r) {
				$(document).trigger("save", [frm.doc]);
				callback(r);
			},
			btn: btn,
			freeze_message: freeze_message,
		});
	};

	var _call = function (opts) {
		// opts = {
		// 	method: "some server method",
		// 	args: {args to be passed},
		// 	callback: callback,
		// 	btn: btn
		// }

		if (nts.ui.form.is_saving) {
			// this is likely to happen if the user presses the shortcut cmd+s for a longer duration or uses double click
			// no need to show this to user, as they can see "Saving" in freeze message
			console.log("Already saving. Please wait a few moments.");
			throw "saving";
		}

		// ensure we remove new docs routes ONLY
		if (frm.is_new()) {
			nts.ui.form.remove_old_form_route();
		}
		nts.ui.form.is_saving = true;

		return nts.call({
			freeze: true,
			// freeze_message: opts.freeze_message,
			method: opts.method,
			args: opts.args,
			btn: opts.btn,
			callback: function (r) {
				opts.callback && opts.callback(r);
			},
			error: opts.error,
			always: function (r) {
				$(btn).prop("disabled", false);
				nts.ui.form.is_saving = false;

				if (r) {
					var doc = r.docs && r.docs[0];
					if (doc) {
						nts.ui.form.update_calling_link(doc);
					}
				}
			},
		});
	};

	if (action === "cancel") {
		cancel();
	} else {
		save();
	}
};

nts.ui.form.check_mandatory = function (frm) {
	var has_errors = false;
	frm.scroll_set = false;

	if (frm.doc.docstatus == 2) return true; // don't check for cancel

	$.each(nts.model.get_all_docs(frm.doc), function (i, doc) {
		var error_fields = [];
		var folded = false;

		$.each(nts.meta.docfield_list[doc.doctype] || [], function (i, docfield) {
			if (docfield.fieldname) {
				const df = nts.meta.get_docfield(doc.doctype, docfield.fieldname, doc.name);

				// skip fields that don't hold data
				if (
					["Section Break", "Column Break", "Tab Break", "HTML", "Heading"].includes(
						df.fieldtype
					)
				) {
					return;
				}

				if (df.fieldtype === "Fold") {
					folded = frm.layout.folded;
				}

				if (
					is_docfield_mandatory(doc, df) &&
					!nts.model.has_value(doc.doctype, doc.name, df.fieldname)
				) {
					has_errors = true;
					error_fields[error_fields.length] = __(df.label, null, df.parent);
					// scroll to field
					if (!frm.scroll_set) {
						scroll_to(doc.parentfield || df.fieldname);
					}

					if (folded) {
						frm.layout.unfold();
						folded = false;
					}
				}
			}
		});

		if (frm.is_new() && frm.meta.autoname === "Prompt" && !frm.doc.__newname) {
			has_errors = true;
			error_fields = [__("Name"), ...error_fields];
		}

		if (error_fields.length) {
			let meta = nts.get_meta(doc.doctype);
			let message;
			if (meta.istable) {
				const table_field = nts.meta.docfield_map[doc.parenttype][doc.parentfield];

				const table_label = __(
					table_field.label || nts.unscrub(table_field.fieldname)
				).bold();

				message = __("Mandatory fields required in table {0}, Row {1}", [
					table_label,
					doc.idx,
				]);
			} else {
				message = __("Mandatory fields required in {0}", [__(doc.doctype)]);
			}
			message = message + "<br><br><ul><li>" + error_fields.join("</li><li>") + "</ul>";
			nts.msgprint({
				message: message,
				indicator: "red",
				title: __("Missing Fields"),
			});
			frm.refresh();
		}
	});

	return !has_errors;

	function is_docfield_mandatory(doc, df) {
		if (df.reqd) return true;
		if (!df.mandatory_depends_on || !doc) return;

		let out = null;
		let expression = df.mandatory_depends_on;
		let parent = nts.get_meta(df.parent);

		if (typeof expression === "boolean") {
			out = expression;
		} else if (typeof expression === "function") {
			out = expression(doc);
		} else if (expression.substr(0, 5) == "eval:") {
			try {
				out = nts.utils.eval(expression.substr(5), { doc, parent });
				if (parent && parent.istable && expression.includes("is_submittable")) {
					out = true;
				}
			} catch (e) {
				nts.throw(__('Invalid "mandatory_depends_on" expression'));
			}
		} else {
			var value = doc[expression];
			if ($.isArray(value)) {
				out = !!value.length;
			} else {
				out = !!value;
			}
		}

		return out;
	}

	function scroll_to(fieldname) {
		if (frm.scroll_to_field(fieldname)) {
			frm.scroll_set = true;
		}
	}
};

nts.ui.form.remove_old_form_route = () => {
	let current_route = nts.get_route().join("/");
	nts.route_history = nts.route_history.filter(
		(route) => route.join("/") !== current_route
	);
};

nts.ui.form.update_calling_link = async (newdoc) => {
	if (!nts._from_link) return;

	const { field_obj, doc, set_route_args, scrollY } = nts._from_link;
	const df = field_obj.df;

	if (!["Link", "Dynamic Link", "Table MultiSelect"].includes(df.fieldtype)) return;

	const is_valid_doctype = () => {
		switch (df.fieldtype) {
			case "Link":
				return newdoc.doctype === df.options;
			case "Dynamic Link":
				return newdoc.doctype === doc[df.options];
			case "Table MultiSelect":
				return newdoc.doctype === field_obj.get_options();
		}
	};

	if (!is_valid_doctype()) return;

	// switch back to the original doc first,
	// this is necessary in case from_link.doctype === newdoc.doctype
	if (field_obj.frm) {
		await nts.set_route(...set_route_args);
		nts.utils.scroll_to(scrollY);
	}

	delete nts._from_link;

	await nts.model.with_doctype(newdoc.doctype);
	const meta = nts.get_meta(newdoc.doctype);

	// update link title cache
	if (meta.title_field && meta.show_title_field_in_link) {
		nts.utils.add_link_title(newdoc.doctype, newdoc.name, newdoc[meta.title_field]);
	}

	// set value
	if (doc && doc.parentfield) {
		const row_exists = field_obj.frm.fields_dict[doc.parentfield].grid.grid_rows.find(
			(row) => row.doc.name === doc.name
		);
		if (row_exists) field_obj.set_value(newdoc.name);
	} else {
		// parsing is needed for table multiselect to convert string to array
		field_obj.parse_validate_and_set_in_model(newdoc.name);
	}

	// refresh field
	field_obj.refresh();
};
