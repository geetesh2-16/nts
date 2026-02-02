import nts
from nts.model.sync import remove_orphan_entities
from nts.modules.export_file import delete_folder
from nts.tests import IntegrationTestCase


class TestRemovingOrphans(IntegrationTestCase):
	def test_removing_orphan(self):
		_before = nts.conf.developer_mode
		nts.conf.developer_mode = True
		# Create a new report
		report = nts.new_doc("Report")
		args = {
			"doctype": "Report",
			"report_name": "Orphan Report",
			"ref_doctype": "DocType",
			"is_standard": "Yes",
			"module": "Custom",
		}
		report.update(args)
		report.save()
		print(f"Created report: {report.name}")
		# delete only fixture (emulating that the export/entity is deleted by the developer)
		delete_folder("Custom", "Report", report.name)
		self.assertTrue(nts.db.exists("Report", report.name))
		if nts.db.exists("Report", report.name):
			remove_orphan_entities()
		self.assertFalse(nts.db.exists("Report", report.name))
		nts.conf.developer_mode = _before
