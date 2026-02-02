# Copyright (c) 2024, nts Technologies and Contributors
# See license.txt

import nts
from nts.desk.form.load import getdoc
from nts.tests import IntegrationTestCase


class TestSystemHealthReport(IntegrationTestCase):
	def test_it_works(self):
		getdoc("System Health Report", "System Health Report")
