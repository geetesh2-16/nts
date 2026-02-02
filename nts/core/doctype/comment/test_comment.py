# Copyright (c) 2019, nts Technologies and Contributors
# License: MIT. See LICENSE
import json

import nts
from nts.templates.includes.comments.comments import add_comment
from nts.tests import IntegrationTestCase
from nts.tests.test_helpers import setup_for_tests
from nts.tests.test_model_utils import set_user

EXTRA_TEST_RECORD_DEPENDENCIES = ["Web Page"]


class TestComment(IntegrationTestCase):
	def setUp(self):
		setup_for_tests()

	def test_comment_creation(self):
		test_doc = nts.get_doc(doctype="ToDo", description="test")
		test_doc.insert()
		comment = test_doc.add_comment("Comment", "test comment")

		test_doc.reload()

		# check if updated in _comments cache
		comments = json.loads(test_doc.get("_comments"))
		self.assertEqual(comments[0].get("name"), comment.name)
		self.assertEqual(comments[0].get("comment"), comment.content)

		# Check comment count
		counts = nts.get_all("ToDo", {"name": test_doc.name}, ["*"], with_comment_count=True)
		self.assertEqual(counts[0]._comment_count, 1)

		comment = test_doc.add_comment("Comment", "test comment")

		counts = nts.get_all("ToDo", {"name": test_doc.name}, ["*"], with_comment_count=True)
		self.assertEqual(counts[0]._comment_count, 2)

		# check document creation
		comment_1 = nts.get_all(
			"Comment",
			fields=["*"],
			filters=dict(reference_doctype=test_doc.doctype, reference_name=test_doc.name),
		)[0]

		self.assertEqual(comment_1.content, "test comment")

	# test via blog
	def test_public_comment(self):
		test_blog = nts.get_doc("Test Blog Post", "_Test Blog Post 1")

		nts.db.delete("Comment", {"reference_doctype": "Test Blog Post"})
		add_comment_args = {
			"comment": "Good comment with 10 chars",
			"comment_email": "test@test.com",
			"comment_by": "Good Tester",
			"reference_doctype": test_blog.doctype,
			"reference_name": test_blog.name,
			"route": f"blog/{test_blog.doctype}/{test_blog.name}",
		}
		add_comment(**add_comment_args)

		self.assertEqual(
			nts.get_all(
				"Comment",
				fields=["*"],
				filters=dict(reference_doctype=test_blog.doctype, reference_name=test_blog.name),
			)[0].published,
			1,
		)

		nts.db.delete("Comment", {"reference_doctype": "Test Blog Post"})

		add_comment_args.update(comment="pleez vizits my site http://mysite.com", comment_by="bad commentor")
		add_comment(**add_comment_args)

		self.assertEqual(
			len(
				nts.get_all(
					"Comment",
					fields=["*"],
					filters=dict(reference_doctype=test_blog.doctype, reference_name=test_blog.name),
				)
			),
			0,
		)

		# test for filtering html and css injection elements
		nts.db.delete("Comment", {"reference_doctype": "Test Blog Post"})

		add_comment_args.update(comment="<script>alert(1)</script>Comment", comment_by="hacker")
		add_comment(**add_comment_args)
		self.assertEqual(
			nts.get_all(
				"Comment",
				fields=["content"],
				filters=dict(reference_doctype=test_blog.doctype, reference_name=test_blog.name),
			)[0]["content"],
			"Comment",
		)

		test_blog.delete()

	def test_user_not_logged_in(self):
		some_system_user = nts.db.get_value("User", {"name": ("not in", nts.STANDARD_USERS)})

		test_blog = nts.get_doc("Web Page", "test-web-page-1")
		with set_user("Guest"):
			self.assertRaises(
				nts.ValidationError,
				add_comment,
				comment="Good comment with 10 chars",
				comment_email=some_system_user,
				comment_by="Good Tester",
				reference_doctype="Web Page",
				reference_name=test_blog.name,
				route=test_blog.route,
			)
