# Copyright (c) 2015, nts Technologies Pvt. Ltd. and Contributors
# License: MIT. See LICENSE
import os
import unittest
from unittest.mock import patch

import nts
from nts.tests import IntegrationTestCase


class TestPage(IntegrationTestCase):
	def test_naming(self):
		self.assertRaises(
			nts.NameError,
			nts.get_doc(doctype="Page", page_name="DocType", module="Core").insert,
		)

	@unittest.skipUnless(
		os.access(nts.get_app_path("nts"), os.W_OK), "Only run if nts app paths is writable"
	)
	@patch.dict(nts.conf, {"developer_mode": 1})
	def test_trashing(self):
		page = nts.new_doc("Page", page_name=nts.generate_hash(), module="Core").insert()

		page.delete()
		nts.db.commit()

		module_path = nts.get_module_path(page.module)
		dir_path = os.path.join(module_path, "page", nts.scrub(page.name))

		self.assertFalse(os.path.exists(dir_path))
