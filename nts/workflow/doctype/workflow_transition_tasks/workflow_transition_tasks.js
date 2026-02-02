// Copyright (c) 2025, nts Technologies and contributors
// For license information, please see license.txt

nts.ui.form.on("Workflow Transition Tasks", {
	refresh: function (frm) {
		nts
			.call({
				method: "nts.workflow.doctype.workflow.workflow.get_workflow_methods",
				type: "GET",
			})
			.then((options) => {
				frm.get_field("tasks").grid.update_docfield_property(
					"task",
					"options",
					options.message
				);
			});
	},
});
