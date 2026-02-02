import nts


def execute():
	nts.db.set_single_value(
		"System Settings",
		{"document_share_key_expiry": 30},
	)
