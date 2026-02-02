# Copyright (c) 2020, nts Technologies and contributors
# License: MIT. See LICENSE

from collections import defaultdict

import nts
from nts.model.document import Document


class ModuleProfile(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from nts.core.doctype.block_module.block_module import BlockModule
		from nts.types import DF

		block_modules: DF.Table[BlockModule]
		module_profile_name: DF.Data
	# end: auto-generated types

	def onload(self):
		from nts.utils.modules import get_modules_from_all_apps

		self.set_onload("all_modules", sorted(m.get("module_name") for m in get_modules_from_all_apps()))

	def get_permission_log_options(self, event=None):
		return {"fields": ["block_modules"]}

	def on_update(self):
		self.clear_cache()
		self.queue_action(
			"update_all_users",
			now=nts.flags.in_test or nts.flags.in_install,
			enqueue_after_commit=True,
		)

	def update_all_users(self):
		"""Changes in module_profile reflected across all its user"""
		block_module = nts.qb.DocType("Block Module")
		user = nts.qb.DocType("User")

		all_current_modules = (
			nts.qb.from_(user)
			.join(block_module)
			.on(user.name == block_module.parent)
			.where(user.module_profile == self.name)
			.select(user.name, block_module.module)
		).run()
		user_modules = defaultdict(set)
		for user, module in all_current_modules:
			user_modules[user].add(module)

		module_profile_modules = {module.module for module in self.block_modules}

		for user_name, modules in user_modules.items():
			if modules != module_profile_modules:
				user = nts.get_doc("User", user_name)
				user.block_modules = []
				for module in module_profile_modules:
					user.append("block_modules", {"module": module})
				user.save()
