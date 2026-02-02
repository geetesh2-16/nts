// Copyright (c) 2025, nts Technologies and contributors
// For license information, please see license.txt

nts.ui.form.on("User Invitation", {
	refresh(frm) {
		nts.xcall("nts.apps.get_apps").then((r) => {
			const apps = r?.map((r) => r.name) ?? [];
			const default_app = "nts";
			frm.set_df_property("app_name", "options", [default_app, ...apps]);
			if (!frm.doc.app_name) {
				frm.set_value("app_name", default_app);
			}
		});
		if (frm.doc.__islocal || frm.doc.status !== "Pending") {
			return;
		}
		frm.add_custom_button(__("Cancel"), () => {
			nts.confirm(__("Are you sure you want to cancel the invitation?"), () =>
				frm.call("cancel_invite")
			);
		});
	},
});
