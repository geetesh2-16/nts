import nts
from nts.modules import load_doctype_module
from nts.website.page_renderers.template_page import TemplatePage


class ListPage(TemplatePage):
	def can_render(self):
		doctype = self.path
		if not doctype or doctype == "Web Page":
			return False

		try:
			meta = nts.get_meta(doctype)
		except nts.DoesNotExistError:
			nts.clear_last_message()
			return False

		if meta.has_web_view:
			return True

		if meta.custom:
			return False

		module = load_doctype_module(doctype)
		return hasattr(module, "get_list_context")

	def render(self):
		nts.form_dict.doctype = self.path
		self.set_standard_path("portal")
		return super().render()
