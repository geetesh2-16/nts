# Copyright (c) 2019, nts Technologies and Contributors
# License: MIT. See LICENSE
import nts
from nts.tests import IntegrationTestCase
from nts.utils import set_request
from nts.website.serve import get_response

EXTRA_TEST_RECORD_DEPENDENCIES = ["Web Page"]


class TestWebsiteRouteMeta(IntegrationTestCase):
	def test_meta_tag_generation(self):
		blogs = nts.get_all(
			"Web Page", fields=["name", "route"], filters={"published": 1, "route": ("!=", "")}, limit=1
		)

		blog = blogs[0]

		# create meta tags for this route
		doc = nts.new_doc("Website Route Meta")
		doc.append("meta_tags", {"key": "type", "value": "web_page"})
		doc.append("meta_tags", {"key": "og:title", "value": "My Web Page"})
		doc.name = blog.route
		doc.insert()

		# set request on this route
		set_request(path=blog.route)
		response = get_response()

		self.assertTrue(response.status_code, 200)

		html = self.normalize_html(response.get_data().decode())

		self.assertIn(self.normalize_html("""<meta name="type" content="web_page">"""), html)
		self.assertIn(self.normalize_html("""<meta property="og:title" content="My Web Page">"""), html)

	def tearDown(self):
		nts.db.rollback()
