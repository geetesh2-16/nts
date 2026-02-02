# Copyright (c) 2023, nts Technologies and Contributors
# See LICENSE

import time

import nts
from nts.core.doctype.doctype.test_doctype import new_doctype
from nts.desk.doctype.bulk_update.bulk_update import submit_cancel_or_update_docs
from nts.tests import IntegrationTestCase, timeout


class TestBulkUpdate(IntegrationTestCase):
	@classmethod
	def setUpClass(cls) -> None:
		super().setUpClass()
		cls.doctype = new_doctype(is_submittable=1, custom=1).insert().name
		cls.child_doctype = new_doctype(istable=1, custom=1).insert().name
		nts.db.commit()
		for _ in range(50):
			nts.new_doc(cls.doctype, some_fieldname=nts.mock("name")).insert()

	@timeout()
	def wait_for_assertion(self, assertion):
		"""Wait till an assertion becomes True"""
		while True:
			if assertion():
				break
			time.sleep(0.2)

	def test_bulk_submit_in_background(self):
		unsubmitted = nts.get_all(self.doctype, {"docstatus": 0}, limit=5, pluck="name")
		failed = submit_cancel_or_update_docs(self.doctype, unsubmitted, action="submit")
		self.assertEqual(failed, [])

		def check_docstatus(docs, status):
			nts.db.rollback()
			matching_docs = nts.get_all(
				self.doctype, {"docstatus": status, "name": ("in", docs)}, pluck="name"
			)
			return set(matching_docs) == set(docs)

		unsubmitted = nts.get_all(self.doctype, {"docstatus": 0}, limit=20, pluck="name")
		submit_cancel_or_update_docs(self.doctype, unsubmitted, action="submit")

		self.wait_for_assertion(lambda: check_docstatus(unsubmitted, 1))

		submitted = nts.get_all(self.doctype, {"docstatus": 1}, limit=20, pluck="name")
		submit_cancel_or_update_docs(self.doctype, submitted, action="cancel")
		self.wait_for_assertion(lambda: check_docstatus(submitted, 2))

	def test_bulk_update_parent_fields(self):
		docnames = nts.get_all(self.doctype, {"docstatus": 0}, limit=5, pluck="name")
		failed = submit_cancel_or_update_docs(
			self.doctype, docnames, action="update", data={"some_fieldname": "_Test Sync"}
		)
		self.assertEqual(failed, [])

		def check_field_values(docs, expected):
			nts.db.rollback()
			values = nts.get_all(self.doctype, {"name": ["in", docs]}, ["name", "some_fieldname"])
			return all(v.some_fieldname == expected for v in values)

		docnames_bg = nts.get_all(self.doctype, {"docstatus": 0}, limit=20, pluck="name")
		submit_cancel_or_update_docs(
			self.doctype, docnames_bg, action="update", data={"some_fieldname": "_Test Background"}
		)

		self.wait_for_assertion(lambda: check_field_values(docnames_bg, "_Test Background"))

	def test_bulk_update_child_fields(self):
		doctype_doc = nts.get_doc("DocType", self.doctype)
		doctype_doc.append(
			"fields", {"fieldname": "child_table", "fieldtype": "Table", "options": self.child_doctype}
		)
		doctype_doc.save()
		nts.db.commit()

		existing_docs = nts.get_all(self.doctype, {"docstatus": 0}, pluck="name")
		for docname in existing_docs:
			doc = nts.get_doc(self.doctype, docname)
			doc.append("child_table", {"some_fieldname": "_Test Child Value"})
			doc.save()
		nts.db.commit()

		update_data = {
			"child_table_updates": {
				self.child_doctype: {"some_fieldname": "_Test Child Updated"},
			}
		}

		def check_child_field(docs, expected):
			nts.db.rollback()
			for docname in docs:
				doc = nts.get_doc(self.doctype, docname)
				if not doc.child_table or doc.child_table[0].some_fieldname != expected:
					return False
			return True

		docnames = nts.get_all(self.doctype, {"docstatus": 0}, limit=5, pluck="name")
		failed = submit_cancel_or_update_docs(self.doctype, docnames, action="update", data=update_data)
		self.assertEqual(failed, [])

		docnames_bg = nts.get_all(self.doctype, {"docstatus": 0}, limit=20, pluck="name")
		submit_cancel_or_update_docs(self.doctype, docnames_bg, action="update", data=update_data)
		self.wait_for_assertion(lambda: check_child_field(docnames_bg, "_Test Child Updated"))
