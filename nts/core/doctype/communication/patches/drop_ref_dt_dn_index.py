import nts
from nts.database.utils import drop_index_if_exists


def execute():
	index_fields = ["reference_doctype", "reference_name"]
	index_name = nts.db.get_index_name(index_fields)
	drop_index_if_exists("tabCommunication", index_name)
