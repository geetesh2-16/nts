# update app in `Module Def` and `Workspace`

import nts
from nts.modules.utils import get_module_app


def execute():
	for module in nts.get_all("Module Def", ["name", "app_name"], filters=dict(custom=0)):
		if not module.app_name:
			try:
				nts.db.set_value("Module Def", module.name, "app_name", get_module_app(module.name))
			except Exception:
				# for some default modules like Home, there is no folder / app
				pass

	for workspace in nts.get_all("Workspace", ["name", "module", "app"]):
		if not workspace.app and workspace.module:
			nts.db.set_value(
				"Workspace",
				workspace.name,
				"app",
				nts.db.get_value("Module Def", workspace.module, "app_name"),
			)
