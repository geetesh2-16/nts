import nts


def execute():
	"""
	Rename the Marketing Campaign table to UTM Campaign table
	"""
	if nts.db.exists("DocType", "UTM Campaign"):
		return

	if not nts.db.exists("DocType", "Marketing Campaign"):
		return

	nts.rename_doc("DocType", "Marketing Campaign", "UTM Campaign", force=True)
	nts.reload_doctype("UTM Campaign", force=True)
