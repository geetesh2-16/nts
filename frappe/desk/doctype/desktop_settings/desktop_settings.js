// Copyright (c) 2025, nts Technologies and contributors
// For license information, please see license.txt

nts.ui.form.on("Desktop Settings", {
	refresh(frm) {
		frm.add_custom_button(__("Visit Desktop"), () => nts.set_route("desktop"));
	},
});
