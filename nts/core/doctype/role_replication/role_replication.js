// Copyright (c) 2024, nts Technologies and contributors
// For license information, please see license.txt

nts.ui.form.on("Role Replication", {
	refresh(frm) {
		frm.disable_save();
		frm.page.set_primary_action(__("Replicate"), ($btn) => {
			$btn.text(__("Replicating..."));
			nts.run_serially([
				() => nts.dom.freeze("Replicating..."),
				() => frm.call("replicate_role"),
				() => nts.dom.unfreeze(),
				() => nts.msgprint(__("Replication completed.")),
				() => $btn.text(__("Replicate")),
			]);
		});
	},
});
